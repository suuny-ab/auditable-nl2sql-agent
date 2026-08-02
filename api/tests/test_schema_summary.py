from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from auditable_nl2sql import (
    DeepSeekSqlGenerator,
    ProviderConfigurationError,
    SCHEMA_SUMMARY_SCHEMA_VERSION,
    SchemaSummaryError,
    build_schema_summary,
    read_schema,
)
from auditable_nl2sql.demo import create_demo_database
from evals.schema_holdout import create_schema_holdout_database


def _schema_snapshot(database_path: Path) -> list[dict[str, Any]]:
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


class RecordingTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
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


class SchemaSummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        root = Path(self.temporary_directory.name)
        self.main_schema = _schema_snapshot(
            create_demo_database(root / "main.sqlite3")
        )
        self.alternate_schema = _schema_snapshot(
            create_schema_holdout_database(root / "alternate.sqlite3")
        )

    def test_main_and_alternate_summaries_are_complete_stable_and_isolated(self) -> None:
        main = build_schema_summary(self.main_schema)
        alternate = build_schema_summary(self.alternate_schema)

        self.assertEqual(main["schema_version"], SCHEMA_SUMMARY_SCHEMA_VERSION)
        self.assertEqual((main["table_count"], main["column_count"]), (4, 17))
        self.assertEqual(
            (alternate["table_count"], alternate["column_count"]),
            (3, 16),
        )
        self.assertEqual(main, build_schema_summary(copy.deepcopy(self.main_schema)))
        self.assertEqual(
            alternate,
            build_schema_summary(copy.deepcopy(self.alternate_schema)),
        )
        self.assertIn('"orders"(', main["text"])
        self.assertIn(
            'fk("customer_id"->"customers"."customer_id")',
            main["text"],
        )
        self.assertNotIn("transaction_lines", main["text"])
        self.assertIn('"transaction_lines"(', alternate["text"])
        self.assertIn('"paid_unit_cents":"INTEGER"', alternate["text"])
        self.assertIn(
            'fk("buyer_key"->"buyer_directory"."buyer_key",'
            '"sku"->"merchandise"."sku")',
            alternate["text"],
        )
        self.assertNotIn("order_items", alternate["text"])

    def test_identifiers_are_json_quoted_instead_of_becoming_instructions(self) -> None:
        summary = build_schema_summary(
            [
                {
                    "name": 'odd\n"table',
                    "columns": [
                        {
                            "name": "field, one",
                            "declared_type": "TEXT",
                            "primary_key_position": 1,
                        }
                    ],
                    "foreign_keys": [],
                }
            ]
        )

        self.assertEqual(summary["table_count"], 1)
        self.assertIn(r'"odd\n\"table"', summary["text"])
        self.assertIn('"field, one":"TEXT":pk1', summary["text"])
        self.assertNotIn('odd\n"table', summary["text"])

    def test_invalid_or_oversized_schema_fails_closed(self) -> None:
        invalid = {
            "empty": [],
            "duplicate table": [self.main_schema[0], copy.deepcopy(self.main_schema[0])],
            "duplicate column": [
                {
                    "name": "items",
                    "columns": [
                        {"name": "id", "declared_type": "TEXT"},
                        {"name": "id", "declared_type": "TEXT"},
                    ],
                    "foreign_keys": [],
                }
            ],
            "invalid primary key": [
                {
                    "name": "items",
                    "columns": [
                        {
                            "name": "id",
                            "declared_type": "TEXT",
                            "primary_key_position": True,
                        }
                    ],
                    "foreign_keys": [],
                }
            ],
            "dangling foreign key": [
                {
                    "name": "items",
                    "columns": [{"name": "id", "declared_type": "TEXT"}],
                    "foreign_keys": [
                        {
                            "column": "missing",
                            "referenced_table": "unknown",
                            "referenced_column": "id",
                        }
                    ],
                }
            ],
            "too many tables": [
                {
                    "name": f"table_{index}",
                    "columns": [{"name": "id", "declared_type": "TEXT"}],
                    "foreign_keys": [],
                }
                for index in range(65)
            ],
        }
        for name, schema in invalid.items():
            with self.subTest(name=name):
                with self.assertRaises(SchemaSummaryError):
                    build_schema_summary(schema)

    def test_provider_injects_summary_for_both_schemas_and_keeps_raw_authority(self) -> None:
        for name, schema in (
            ("main", self.main_schema),
            ("alternate", self.alternate_schema),
        ):
            with self.subTest(name=name):
                transport = RecordingTransport()
                generator = DeepSeekSqlGenerator(enabled=True, transport=transport)
                generator.generate("列出全部订单。", schema)

                self.assertEqual(len(transport.calls), 1)
                messages = transport.calls[0]["messages"]
                user_input = json.loads(messages[1]["content"].split("\n", 1)[1])
                self.assertEqual(user_input["schema"], schema)
                self.assertEqual(
                    user_input["schema_summary"],
                    build_schema_summary(schema),
                )
                self.assertIn("full schema is authoritative", messages[0]["content"])
                self.assertIn("Never infer stored values", messages[0]["content"])

    def test_invalid_summary_prevents_transport(self) -> None:
        transport = RecordingTransport()
        generator = DeepSeekSqlGenerator(enabled=True, transport=transport)
        invalid_schema = [
            {
                "name": "items",
                "columns": [
                    {
                        "name": "id",
                        "declared_type": "TEXT",
                        "primary_key_position": -1,
                    }
                ],
                "foreign_keys": [],
            }
        ]

        with self.assertRaisesRegex(
            ProviderConfigurationError,
            "Schema summary is invalid",
        ):
            generator.generate("列出全部订单。", invalid_schema)
        self.assertEqual(transport.calls, [])


if __name__ == "__main__":
    unittest.main()
