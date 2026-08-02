from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from auditable_nl2sql import (
    SCHEMA_KNOWLEDGE_SCHEMA_VERSION,
    DeepSeekSqlGenerator,
    SchemaKnowledgeError,
    build_business_context,
    build_schema_knowledge,
    read_schema,
)
from auditable_nl2sql.demo import create_demo_database
from evals.schema_holdout import create_schema_holdout_database


def _schema_snapshot(database_path: Path) -> list[dict[str, object]]:
    return [
        {
            "name": table.name,
            "columns": [
                {
                    "name": column.name,
                    "declared_type": column.declared_type,
                    "nullable": column.nullable,
                    "primary_key_position": column.primary_key_position,
                    "default_value": column.default_value,
                }
                for column in table.columns
            ],
            "foreign_keys": [
                {
                    "column": key.column,
                    "referenced_table": key.referenced_table,
                    "referenced_column": key.referenced_column,
                }
                for key in table.foreign_keys
            ],
        }
        for table in read_schema(database_path)
    ]


class SchemaKnowledgeBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        root = Path(self.temporary_directory.name)
        self.root = root
        database = create_schema_holdout_database(root / "business.sqlite3")
        self.schema = _schema_snapshot(database)

    def test_builder_recognizes_the_main_and_alternate_schema_roles(self) -> None:
        main_schema = _schema_snapshot(
            create_demo_database(self.root / "main-business.sqlite3")
        )
        main = build_schema_knowledge(main_schema)
        alternate = build_schema_knowledge(self.schema)

        self.assertEqual(len(main.field_descriptions), 17)
        self.assertEqual(len(alternate.field_descriptions), 16)
        main_terms = {term.term: term for term in main.candidate_terms}
        alternate_terms = {term.term: term for term in alternate.candidate_terms}
        self.assertTrue(
            {
                "order_items.quantity",
                "order_items.unit_price",
                "orders.order_id",
                "orders.status",
            }
            <= set(main_terms["销售额"].related_fields)
        )
        self.assertTrue(
            {
                "transaction_lines.units",
                "transaction_lines.paid_unit_cents",
                "transaction_lines.ticket_no",
                "transaction_lines.state_code",
            }
            <= set(alternate_terms["销售额"].related_fields)
        )

    def test_builds_deterministic_notes_and_terms_for_alternate_schema(self) -> None:
        first = build_schema_knowledge(self.schema)
        second = build_schema_knowledge(copy.deepcopy(self.schema))

        self.assertEqual(first, second)
        self.assertEqual(first.schema_version, SCHEMA_KNOWLEDGE_SCHEMA_VERSION)
        references = {note.reference for note in first.field_descriptions}
        schema_references = {
            f"{table['name']}.{column['name']}"
            for table in self.schema
            for column in table["columns"]
        }
        self.assertEqual(references, schema_references)
        self.assertEqual(len(references), 16)
        self.assertTrue(
            all(
                set(term.related_fields) <= schema_references
                for term in first.candidate_terms
            )
        )
        self.assertEqual(
            [term.term for term in first.candidate_terms],
            [
                "销售额",
                "非取消订单",
                "订单",
                "订单商品明细",
                "商品",
                "销售渠道",
                "客户",
                "区域",
                "客户分群",
                "客单价",
                "成交单价",
                "标价",
                "数量",
            ],
        )
        notes = {note.reference: note.description for note in first.field_descriptions}
        self.assertIn("除以 100", notes["transaction_lines.paid_unit_cents"])
        self.assertIn("实际存储值不能由字段名臆造", notes["transaction_lines.state_code"])
        self.assertIn(
            "外键关联 buyer_directory.buyer_key",
            notes["transaction_lines.buyer_key"],
        )

    def test_alternate_context_uses_generated_knowledge_without_old_sql(self) -> None:
        context = build_business_context(
            "非取消订单按销售渠道统计销售额，结果从高到低是什么？",
            self.schema,
        )

        self.assertEqual(context["schema_version"], "business-context-v3")
        self.assertEqual(
            [term["term"] for term in context["matched_terms"]],
            ["销售额", "非取消订单", "订单", "销售渠道"],
        )
        references = {
            f"{note['table']}.{note['field']}" for note in context["field_notes"]
        }
        self.assertTrue(
            {
                "transaction_lines.ticket_no",
                "transaction_lines.state_code",
                "transaction_lines.source_code",
                "transaction_lines.units",
                "transaction_lines.paid_unit_cents",
            }
            <= references
        )
        self.assertEqual(context["training_examples"], [])

    def test_provider_request_receives_the_generated_context(self) -> None:
        class RecordingTransport:
            def __init__(self) -> None:
                self.requests: list[dict[str, object]] = []

            def complete(self, payload: dict[str, object]) -> dict[str, object]:
                self.requests.append(payload)
                return {
                    "model": "fake-model",
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "content": json.dumps(
                                    {
                                        "action": "query",
                                        "sql": "SELECT 1",
                                        "reason": "fake deterministic response",
                                    }
                                )
                            },
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 2,
                        "total_tokens": 12,
                    },
                }

        transport = RecordingTransport()
        generator = DeepSeekSqlGenerator(enabled=True, transport=transport)
        generator.generate(
            "非取消订单按销售渠道统计销售额，结果从高到低是什么？",
            self.schema,
        )

        self.assertEqual(len(transport.requests), 1)
        messages = transport.requests[0]["messages"]
        user_input = json.loads(messages[1]["content"].split("\n", 1)[1])
        context = user_input["business_context"]
        self.assertEqual(
            [term["term"] for term in context["matched_terms"]],
            ["销售额", "非取消订单", "订单", "销售渠道"],
        )
        self.assertEqual(context["training_examples"], [])

    def test_line_detail_question_gets_quantity_and_price_roles(self) -> None:
        context = build_business_context(
            "订单 O1001 包含哪些商品、数量、单价和行金额？",
            self.schema,
        )

        terms = {term["term"] for term in context["matched_terms"]}
        self.assertTrue({"订单", "订单商品明细", "商品", "数量"} <= terms)
        references = {
            f"{note['table']}.{note['field']}" for note in context["field_notes"]
        }
        self.assertTrue(
            {
                "merchandise.sku",
                "merchandise.title",
                "transaction_lines.ticket_no",
                "transaction_lines.sku",
                "transaction_lines.units",
                "transaction_lines.paid_unit_cents",
            }
            <= references
        )

    def test_rejects_duplicate_fields_and_dangling_foreign_keys(self) -> None:
        duplicate = copy.deepcopy(self.schema)
        duplicate[0]["columns"].append(copy.deepcopy(duplicate[0]["columns"][0]))
        dangling = copy.deepcopy(self.schema)
        dangling[-1]["foreign_keys"][0]["referenced_column"] = "missing"

        for invalid in (duplicate, dangling):
            with self.subTest(invalid=invalid):
                with self.assertRaises(SchemaKnowledgeError):
                    build_schema_knowledge(invalid)


if __name__ == "__main__":
    unittest.main()
