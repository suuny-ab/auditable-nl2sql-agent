from __future__ import annotations

import copy
from dataclasses import replace
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import auditable_nl2sql.knowledge as knowledge_module
from auditable_nl2sql import (
    BUSINESS_CONTEXT_SCHEMA_VERSION,
    BusinessKnowledgeError,
    ENUM_VALUE_MAX_MATCHES,
    TRAINING_PAIR_MAX_MATCHES,
    TRAINING_PAIR_SIMILARITY_THRESHOLD,
    build_business_context,
    execute_read_only,
    load_business_knowledge,
    read_schema,
    retrieve_training_examples,
)
from auditable_nl2sql.demo import create_demo_database
from evals.contract import load_cases, validate_case_contract


PROJECT_ROOT = Path(__file__).resolve().parents[2]


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
                    "column": foreign_key.column,
                    "referenced_table": foreign_key.referenced_table,
                    "referenced_column": foreign_key.referenced_column,
                }
                for foreign_key in table.foreign_keys
            ],
        }
        for table in read_schema(database_path)
    ]


class BusinessKnowledgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        root = Path(self.temporary_directory.name)
        self.database = create_demo_database(root / "business.sqlite3")
        self.schema = _schema_snapshot(self.database)

    def test_terms_are_unique_and_field_notes_cover_the_demo_schema(self) -> None:
        knowledge = load_business_knowledge()

        self.assertEqual(len(knowledge.terms), 10)
        aliases = [
            alias.casefold()
            for term in knowledge.terms
            for alias in (term.term, *term.synonyms)
        ]
        self.assertEqual(len(aliases), len(set(aliases)))

        described_fields = {
            description.reference for description in knowledge.field_descriptions
        }
        schema_fields = {
            f"{table['name']}.{column['name']}"
            for table in self.schema
            for column in table["columns"]
        }
        self.assertEqual(described_fields, schema_fields)
        self.assertEqual(len(described_fields), 17)
        for term in knowledge.terms:
            self.assertTrue(term.synonyms)
            self.assertTrue(term.definition)
            self.assertTrue(set(term.related_fields) <= described_fields)

    def test_training_pairs_cover_all_observed_success_cases(self) -> None:
        cases = load_cases(PROJECT_ROOT / "evals/cases.jsonl")
        validate_case_contract(cases)
        expected = [
            (case["case_id"], case["question"], case["reference_sql"])
            for case in cases
            if case["case_id"] in {f"success-{index:03d}" for index in range(1, 17)}
        ]
        training_pairs = load_business_knowledge().training_pairs
        actual = [
            (pair.source_case_id, pair.question, pair.sql)
            for pair in training_pairs
        ]

        self.assertEqual(actual, expected)
        self.assertTrue(all(pair.enabled for pair in training_pairs))
        self.assertEqual(
            {pair.source_case_id for pair in training_pairs},
            {f"success-{index:03d}" for index in range(1, 17)},
        )

    def test_enum_values_cover_only_closed_fields_and_match_the_fixture(self) -> None:
        knowledge = load_business_knowledge()
        self.assertEqual(
            set(knowledge.enum_tables),
            {"customers", "products", "orders", "order_items"},
        )
        self.assertEqual(len(knowledge.enum_values), 17)
        self.assertLess(ENUM_VALUE_MAX_MATCHES, len(knowledge.enum_values))

        expected = {
            "customers.region": {"华东", "华南", "华北", "西南"},
            "customers.segment": {"企业", "零售"},
            "products.category": {"户外", "家居", "数码", "办公"},
            "orders.status": {"paid", "shipped", "completed", "cancelled"},
            "orders.sales_channel": {"online", "store", "marketplace"},
        }
        indexed: dict[str, set[str]] = {}
        aliases: list[str] = []
        for enum_value in knowledge.enum_values:
            indexed.setdefault(enum_value.reference, set()).add(enum_value.value)
            aliases.extend(
                alias.casefold()
                for alias in (enum_value.value, *enum_value.aliases)
            )
        self.assertEqual(indexed, expected)
        self.assertEqual(len(aliases), len(set(aliases)))
        self.assertFalse(
            any(reference.startswith("order_items.") for reference in indexed)
        )

        for reference, values in expected.items():
            table, field = reference.split(".")
            result = execute_read_only(
                self.database,
                f'SELECT DISTINCT "{field}" FROM "{table}" ORDER BY "{field}"',
            )
            self.assertFalse(result.truncated)
            self.assertEqual({row[0] for row in result.rows}, values)

    def test_enum_value_contract_rejects_unknowns_and_duplicates(self) -> None:
        resource_names = (
            "business_terms.json",
            "field_descriptions.json",
            "enum_values.json",
            "training_pairs.json",
        )
        resources = {
            name: copy.deepcopy(knowledge_module._read_resource(name))
            for name in resource_names
        }
        invalid_payloads = []

        unknown_root = copy.deepcopy(resources["enum_values.json"])
        unknown_root["unexpected"] = True
        invalid_payloads.append(unknown_root)

        unknown_field = copy.deepcopy(resources["enum_values.json"])
        unknown_field["tables"][0]["fields"][0]["name"] = "not_a_field"
        invalid_payloads.append(unknown_field)

        duplicate_alias = copy.deepcopy(resources["enum_values.json"])
        duplicate_alias["tables"][0]["fields"][0]["values"][1]["aliases"][0] = (
            "华东"
        )
        invalid_payloads.append(duplicate_alias)

        for invalid_enum_values in invalid_payloads:
            with self.subTest(invalid_enum_values=invalid_enum_values):
                knowledge_module.load_business_knowledge.cache_clear()

                def fake_read_resource(name: str) -> object:
                    if name == "enum_values.json":
                        return invalid_enum_values
                    return resources[name]

                with patch.object(
                    knowledge_module,
                    "_read_resource",
                    side_effect=fake_read_resource,
                ):
                    with self.assertRaises(BusinessKnowledgeError):
                        knowledge_module.load_business_knowledge()
        knowledge_module.load_business_knowledge.cache_clear()

    def test_similar_question_recalls_enabled_training_pair(self) -> None:
        examples = retrieve_training_examples(
            "2026年第一季度非取消订单的销售额是多少？"
        )

        self.assertLessEqual(len(examples), TRAINING_PAIR_MAX_MATCHES)
        self.assertEqual(examples[0]["source_case_id"], "success-001")
        self.assertGreaterEqual(
            examples[0]["similarity"],
            TRAINING_PAIR_SIMILARITY_THRESHOLD,
        )
        self.assertLess(examples[0]["similarity"], 1.0)

    def _assert_observed_case_recall(
        self,
        case_id: str,
        expected_alias: str,
    ) -> None:
        cases = load_cases(PROJECT_ROOT / "evals/cases.jsonl")
        case = next(item for item in cases if item["case_id"] == case_id)

        examples = retrieve_training_examples(case["question"])

        self.assertLessEqual(len(examples), TRAINING_PAIR_MAX_MATCHES)
        self.assertEqual(examples[0]["source_case_id"], case_id)
        self.assertEqual(examples[0]["question"], case["question"])
        self.assertEqual(examples[0]["sql"], case["reference_sql"])
        self.assertEqual(examples[0]["similarity"], 1.0)
        self.assertIn("LIMIT 5", examples[0]["sql"])
        self.assertIn(expected_alias, examples[0]["sql"])

    def test_success_009_recalls_bounded_order_month_reference(self) -> None:
        self._assert_observed_case_recall("success-009", "AS order_month")

    def test_success_010_recalls_bounded_region_reference(self) -> None:
        self._assert_observed_case_recall("success-010", "AS order_count")

    def test_success_011_recalls_bounded_units_sold_reference(self) -> None:
        self._assert_observed_case_recall("success-011", "AS units_sold")

    def test_success_012_recalls_bounded_customer_reference(self) -> None:
        self._assert_observed_case_recall("success-012", "AS order_count")

    def test_success_013_recalls_bounded_discount_reference(self) -> None:
        self._assert_observed_case_recall("success-013", "AS max_unit_discount")

    def test_success_014_recalls_bounded_average_order_reference(self) -> None:
        self._assert_observed_case_recall("success-014", "AS avg_order_revenue")

    def test_success_015_recalls_bounded_order_threshold_reference(self) -> None:
        self._assert_observed_case_recall("success-015", "AS revenue")

    def test_success_016_recalls_bounded_channel_top_order_reference(self) -> None:
        self._assert_observed_case_recall("success-016", "AS revenue_rank")

    def test_unrelated_question_does_not_recall_training_pair(self) -> None:
        self.assertEqual(retrieve_training_examples("明天会下雨吗？"), [])

    def test_disabled_training_pair_is_not_recalled(self) -> None:
        enabled = load_business_knowledge().training_pairs[0]
        disabled = replace(enabled, enabled=False)

        self.assertEqual(
            retrieve_training_examples(
                enabled.question,
                training_pairs=(disabled,),
            ),
            [],
        )

    def test_matches_terms_and_injects_only_related_available_field_notes(self) -> None:
        context = build_business_context(
            "按有效订单的营收统计下单渠道。",
            self.schema,
        )

        self.assertEqual(context["schema_version"], BUSINESS_CONTEXT_SCHEMA_VERSION)
        self.assertEqual(
            [term["term"] for term in context["matched_terms"]],
            ["销售额", "非取消订单", "订单", "销售渠道"],
        )
        self.assertEqual(context["matched_terms"][0]["matched_by"], ["营收"])
        references = {
            f"{note['table']}.{note['field']}" for note in context["field_notes"]
        }
        self.assertEqual(
            references,
            {
                "order_items.quantity",
                "order_items.unit_price",
                "orders.customer_id",
                "orders.order_date",
                "orders.order_id",
                "orders.sales_channel",
                "orders.status",
            },
        )
        self.assertNotIn("products.list_price", references)
        self.assertNotIn("customers.segment", references)

    def test_enum_value_matches_are_stable_and_require_an_available_field(self) -> None:
        question = "华东地区已完成订单有多少笔？"
        context = build_business_context(question, self.schema)

        self.assertEqual(
            context["enum_values"],
            [
                {
                    "table": "customers",
                    "field": "region",
                    "value": "华东",
                    "matched_by": ["华东", "华东地区"],
                },
                {
                    "table": "orders",
                    "field": "status",
                    "value": "completed",
                    "matched_by": ["已完成", "完成订单"],
                },
            ],
        )

        schema_without_status = copy.deepcopy(self.schema)
        orders = next(
            table for table in schema_without_status if table["name"] == "orders"
        )
        orders["columns"] = [
            column for column in orders["columns"] if column["name"] != "status"
        ]
        context_without_status = build_business_context(
            question,
            schema_without_status,
        )
        self.assertEqual(
            context_without_status["enum_values"],
            context["enum_values"][:1],
        )

        bounded = build_business_context(
            "华东华南华北西南企业零售户外家居数码办公",
            self.schema,
        )
        self.assertEqual(len(bounded["enum_values"]), ENUM_VALUE_MAX_MATCHES)

    def test_no_match_produces_an_empty_bounded_context(self) -> None:
        context = build_business_context("明天会下雨吗？", self.schema)

        self.assertEqual(
            context,
            {
                "schema_version": "business-context-v3",
                "matched_terms": [],
                "field_notes": [],
                "enum_values": [],
                "training_examples": [],
            },
        )


if __name__ == "__main__":
    unittest.main()
