from __future__ import annotations

from dataclasses import replace
import tempfile
import unittest
from pathlib import Path

from auditable_nl2sql import (
    BUSINESS_CONTEXT_SCHEMA_VERSION,
    TRAINING_PAIR_MAX_MATCHES,
    TRAINING_PAIR_SIMILARITY_THRESHOLD,
    build_business_context,
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

    def test_training_pairs_cover_only_the_original_frozen_success_cases(self) -> None:
        cases = load_cases(PROJECT_ROOT / "evals/cases.jsonl")
        validate_case_contract(cases)
        expected = [
            (case["case_id"], case["question"], case["reference_sql"])
            for case in cases
            if case["case_id"] in {f"success-{index:03d}" for index in range(1, 9)}
        ]
        training_pairs = load_business_knowledge().training_pairs
        actual = [
            (pair.source_case_id, pair.question, pair.sql)
            for pair in training_pairs
        ]

        self.assertEqual(actual, expected)
        self.assertTrue(all(pair.enabled for pair in training_pairs))
        self.assertTrue(
            {f"success-{index:03d}" for index in range(9, 13)}.isdisjoint(
                {pair.source_case_id for pair in training_pairs}
            )
        )

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

    def test_no_match_produces_an_empty_bounded_context(self) -> None:
        context = build_business_context("明天会下雨吗？", self.schema)

        self.assertEqual(
            context,
            {
                "schema_version": "business-context-v2",
                "matched_terms": [],
                "field_notes": [],
                "training_examples": [],
            },
        )


if __name__ == "__main__":
    unittest.main()
