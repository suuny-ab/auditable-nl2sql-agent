from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from importlib import resources
from pathlib import Path

from auditable_nl2sql import (
    BUSINESS_CONTEXT_SCHEMA_VERSION,
    DEFAULT_DATASOURCE_ID,
    SCHEMA_HOLDOUT_DATASOURCE_ID,
    BusinessKnowledgeError,
    DeepSeekSqlGenerator,
    ProviderConfigurationError,
    build_business_context,
    build_schema_knowledge,
    load_business_knowledge,
    read_schema,
)
from auditable_nl2sql.demo import create_demo_database
from evals.contract import load_cases
from evals.schema_holdout import create_schema_holdout_database


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESOURCE_NAMES = (
    "manifest.json",
    "business_terms.json",
    "field_descriptions.json",
    "enum_values.json",
    "training_pairs.json",
)
MAIN_CONTEXTS_V3_SHA256 = (
    "29980F9AA5EC0B7AB2E727BC60E7CCAB7FA16EBA107E4D48052C58B57457ABEE"
)
HOLDOUT_NATIVE_CONTEXTS_V3_SHA256 = (
    "F62CDCC0006ED9C3EC94D20D97741D27AEF2082B22AD17429D9F2C7DB36A27C7"
)


def _schema_snapshot(database_path: Path) -> list[dict[str, object]]:
    snapshot: list[dict[str, object]] = []
    for table in read_schema(database_path):
        table_payload: dict[str, object] = {
            "name": table.name,
            "columns": [],
            "foreign_keys": [
                {
                    "column": key.column,
                    "referenced_table": key.referenced_table,
                    "referenced_column": key.referenced_column,
                }
                for key in table.foreign_keys
            ],
        }
        if table.description is not None:
            table_payload["description"] = table.description
        for column in table.columns:
            column_payload: dict[str, object] = {
                "name": column.name,
                "declared_type": column.declared_type,
                "nullable": column.nullable,
                "primary_key_position": column.primary_key_position,
                "default_value": column.default_value,
            }
            if column.description is not None:
                column_payload["description"] = column.description
            table_payload["columns"].append(column_payload)
        snapshot.append(table_payload)
    return snapshot


def _legacy_context_digest(contexts: list[dict[str, object]]) -> str:
    legacy = []
    for context in contexts:
        self_describing = dict(context)
        self_describing.pop("datasource_id")
        self_describing["schema_version"] = "business-context-v3"
        legacy.append(self_describing)
    encoded = json.dumps(
        legacy,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


class DatasourceGovernanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        root = Path(self.temporary_directory.name)
        self.main_schema = _schema_snapshot(
            create_demo_database(root / "main.sqlite3")
        )
        self.holdout_schema = _schema_snapshot(
            create_schema_holdout_database(root / "holdout.sqlite3")
        )

    def test_resources_are_physically_isolated_by_datasource(self) -> None:
        data_root = resources.files("auditable_nl2sql").joinpath("data")
        namespaces = data_root.joinpath("datasources")

        for datasource_id in (
            DEFAULT_DATASOURCE_ID,
            SCHEMA_HOLDOUT_DATASOURCE_ID,
        ):
            with self.subTest(datasource_id=datasource_id):
                namespace = namespaces.joinpath(datasource_id)
                self.assertTrue(namespace.is_dir())
                self.assertEqual(
                    {item.name for item in namespace.iterdir()},
                    set(RESOURCE_NAMES),
                )
        for resource_name in RESOURCE_NAMES[1:]:
            self.assertFalse(data_root.joinpath(resource_name).is_file())

    def test_default_and_native_holdout_contexts_are_digest_locked(self) -> None:
        cases = load_cases(PROJECT_ROOT / "evals/cases.jsonl")
        holdout_cases = load_cases(
            PROJECT_ROOT / "evals/schema_holdout_cases.jsonl"
        )
        main_contexts = [
            build_business_context(
                case["question"],
                self.main_schema,
                datasource_id=DEFAULT_DATASOURCE_ID,
            )
            for case in cases
        ]
        holdout_contexts = [
            build_business_context(
                case["question"],
                self.holdout_schema,
                datasource_id=SCHEMA_HOLDOUT_DATASOURCE_ID,
            )
            for case in holdout_cases
        ]

        self.assertEqual(len(main_contexts), 40)
        self.assertEqual(len(holdout_contexts), 15)
        self.assertTrue(
            all(
                context["schema_version"] == BUSINESS_CONTEXT_SCHEMA_VERSION
                and context["datasource_id"] == DEFAULT_DATASOURCE_ID
                for context in main_contexts
            )
        )
        self.assertTrue(
            all(
                context["schema_version"] == BUSINESS_CONTEXT_SCHEMA_VERSION
                and context["datasource_id"] == SCHEMA_HOLDOUT_DATASOURCE_ID
                for context in holdout_contexts
            )
        )
        self.assertEqual(
            _legacy_context_digest(main_contexts),
            MAIN_CONTEXTS_V3_SHA256,
        )
        self.assertEqual(
            _legacy_context_digest(holdout_contexts),
            HOLDOUT_NATIVE_CONTEXTS_V3_SHA256,
        )

    def test_holdout_namespace_equals_deterministic_builder_artifacts(self) -> None:
        knowledge = load_business_knowledge(SCHEMA_HOLDOUT_DATASOURCE_ID)
        derived = build_schema_knowledge(self.holdout_schema)

        self.assertEqual(knowledge.datasource_id, SCHEMA_HOLDOUT_DATASOURCE_ID)
        self.assertEqual(
            [
                (term.term, term.synonyms, term.definition, term.related_fields)
                for term in knowledge.terms
            ],
            [
                (term.term, term.synonyms, term.definition, term.related_fields)
                for term in derived.candidate_terms
            ],
        )
        self.assertEqual(
            [
                (
                    note.table,
                    note.table_description,
                    note.field,
                    note.description,
                )
                for note in knowledge.field_descriptions
            ],
            [
                (
                    note.table,
                    note.table_description,
                    note.field,
                    note.description,
                )
                for note in derived.field_descriptions
            ],
        )
        self.assertEqual(knowledge.enum_values, ())
        self.assertEqual(knowledge.training_pairs, ())
        self.assertTrue(
            all(
                reference.startswith(
                    ("buyer_directory.", "merchandise.", "transaction_lines.")
                )
                for term in knowledge.terms
                for reference in term.related_fields
            )
        )

    def test_cross_datasource_binding_fails_before_transport(self) -> None:
        class RecordingTransport:
            def __init__(self) -> None:
                self.calls: list[dict[str, object]] = []

            def complete(self, payload: dict[str, object]) -> dict[str, object]:
                self.calls.append(payload)
                raise AssertionError("cross-source request reached transport")

        for datasource_id, schema in (
            (DEFAULT_DATASOURCE_ID, self.holdout_schema),
            (SCHEMA_HOLDOUT_DATASOURCE_ID, self.main_schema),
        ):
            with self.subTest(datasource_id=datasource_id):
                transport = RecordingTransport()
                generator = DeepSeekSqlGenerator(
                    enabled=True,
                    transport=transport,
                    datasource_id=datasource_id,
                )
                with self.assertRaises(ProviderConfigurationError):
                    generator.generate("非取消订单销售额是多少？", schema)
                self.assertEqual(transport.calls, [])

    def test_invalid_or_unknown_datasource_fails_closed(self) -> None:
        for datasource_id in ("../escape", "unknown-source"):
            with self.subTest(datasource_id=datasource_id):
                with self.assertRaises(BusinessKnowledgeError):
                    load_business_knowledge(datasource_id)


if __name__ == "__main__":
    unittest.main()
