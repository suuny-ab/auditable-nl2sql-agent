from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from auditable_nl2sql import (
    DEFAULT_MAX_CANDIDATE_FIELDS,
    DEFAULT_MAX_DISTINCT_VALUES,
    DEFAULT_MAX_VALUE_CHARS,
    DEFAULT_VALUE_COLLECTION_TIMEOUT_SECONDS,
    SCHEMA_HOLDOUT_DATASOURCE_ID,
    ValueCollectionError,
    build_business_context,
    build_enum_values_payload,
    collect_low_cardinality_values,
    read_schema,
)
from evals.schema_holdout import create_schema_holdout_database


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot(database_path: Path) -> list[dict[str, object]]:
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


class ValueCollectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)

    def test_holdout_collection_is_bounded_deterministic_and_read_only(self) -> None:
        database = create_schema_holdout_database(self.root / "holdout.sqlite3")
        before = _sha256(database)

        collection = collect_low_cardinality_values(database)
        payload = build_enum_values_payload(collection)

        self.assertEqual(_sha256(database), before)
        self.assertEqual(collection.max_distinct_values, DEFAULT_MAX_DISTINCT_VALUES)
        self.assertEqual(collection.max_candidate_fields, DEFAULT_MAX_CANDIDATE_FIELDS)
        self.assertEqual(collection.max_value_chars, DEFAULT_MAX_VALUE_CHARS)
        self.assertEqual(
            collection.timeout_seconds,
            DEFAULT_VALUE_COLLECTION_TIMEOUT_SECONDS,
        )
        self.assertEqual(collection.candidate_field_count, 5)
        self.assertEqual(collection.collected_field_count, 5)
        self.assertEqual(collection.skipped_high_cardinality_fields, ())
        self.assertEqual(collection.skipped_unsafe_value_fields, ())
        self.assertEqual(
            {
                field.reference: field.values
                for field in collection.fields
            },
            {
                "buyer_directory.buyer_class": ("企业", "零售"),
                "buyer_directory.market_area": ("华东", "华北", "华南", "西南"),
                "merchandise.department": ("办公", "家居", "户外", "数码"),
                "transaction_lines.source_code": ("PLATFORM", "SHOP", "WEB"),
                "transaction_lines.state_code": (
                    "CLOSED",
                    "IN_TRANSIT",
                    "SETTLED",
                    "VOID",
                ),
            },
        )
        packaged = json.loads(
            (
                PROJECT_ROOT
                / "api/src/auditable_nl2sql/data/datasources/"
                "schema-holdout-v1/enum_values.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(payload, packaged)
        self.assertTrue(
            all(
                value["aliases"] == []
                for table in payload["tables"]
                for field in table["fields"]
                for value in field["values"]
            )
        )

    def test_high_cardinality_and_ineligible_fields_are_not_sampled_as_enums(self) -> None:
        database = self.root / "bounded.sqlite3"
        with closing(sqlite3.connect(database)) as connection:
            connection.executescript(
                '''
                CREATE TABLE "odd table" (
                    record_id TEXT PRIMARY KEY,
                    "sales channel" TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    occurred_on TEXT NOT NULL,
                    amount INTEGER NOT NULL
                );
                '''
            )
            connection.executemany(
                'INSERT INTO "odd table" VALUES (?, ?, ?, ?, ?, ?)',
                [
                    (
                        f"ID-{index:02d}",
                        "WEB" if index % 2 else "SHOP",
                        f"priority-{index:02d}",
                        f"name-{index:02d}",
                        f"2026-01-{index:02d}",
                        index,
                    )
                    for index in range(1, 21)
                ],
            )
            connection.commit()
        before = _sha256(database)

        collection = collect_low_cardinality_values(
            database,
            max_distinct_values=4,
        )

        self.assertEqual(_sha256(database), before)
        self.assertEqual(
            [(field.reference, field.values) for field in collection.fields],
            [("odd table.sales channel", ("SHOP", "WEB"))],
        )
        self.assertEqual(collection.candidate_field_count, 2)
        self.assertEqual(
            collection.skipped_high_cardinality_fields,
            ("odd table.priority",),
        )
        self.assertNotIn("priority-01", repr(collection))

    def test_invalid_limits_and_excess_candidate_fields_fail_closed(self) -> None:
        database = self.root / "limits.sqlite3"
        with closing(sqlite3.connect(database)) as connection:
            connection.execute(
                "CREATE TABLE sample (alpha TEXT, beta TEXT, gamma TEXT)"
            )
            connection.execute("INSERT INTO sample VALUES ('a', 'b', 'c')")
            connection.commit()

        invalid_arguments = (
            {"max_distinct_values": 0},
            {"max_distinct_values": 65},
            {"max_candidate_fields": 0},
            {"max_candidate_fields": 129},
            {"max_value_chars": 0},
            {"max_value_chars": 1025},
            {"timeout_seconds": 0},
            {"timeout_seconds": 10.1},
        )
        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments):
                with self.assertRaises(ValueCollectionError):
                    collect_low_cardinality_values(database, **arguments)

        with self.assertRaises(ValueCollectionError):
            collect_low_cardinality_values(database, max_candidate_fields=2)

    def test_schema_derived_related_values_enter_context_without_runtime_scan(self) -> None:
        database = create_schema_holdout_database(self.root / "context.sqlite3")
        schema = _snapshot(database)

        with patch(
            "auditable_nl2sql.value_collection.collect_low_cardinality_values",
            side_effect=AssertionError("runtime attempted a row scan"),
        ) as collector:
            context = build_business_context(
                "非取消订单按销售渠道统计销售额，结果从高到低是什么？",
                schema,
                datasource_id=SCHEMA_HOLDOUT_DATASOURCE_ID,
            )

        collector.assert_not_called()
        self.assertEqual(
            [
                (
                    f"{item['table']}.{item['field']}",
                    item["value"],
                    item["matched_by"],
                )
                for item in context["enum_values"]
            ],
            [
                ("transaction_lines.source_code", "PLATFORM", []),
                ("transaction_lines.source_code", "SHOP", []),
                ("transaction_lines.source_code", "WEB", []),
                ("transaction_lines.state_code", "CLOSED", []),
                ("transaction_lines.state_code", "IN_TRANSIT", []),
                ("transaction_lines.state_code", "SETTLED", []),
                ("transaction_lines.state_code", "VOID", []),
            ],
        )


if __name__ == "__main__":
    unittest.main()
