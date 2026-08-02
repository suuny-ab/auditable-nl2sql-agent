from __future__ import annotations

import hashlib
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from auditable_nl2sql import (
    SCHEMA_HOLDOUT_DATASOURCE_ID,
    SchemaKnowledgeError,
    build_schema_knowledge,
    load_business_knowledge,
    merge_description_layers,
    read_schema,
)
from auditable_nl2sql.demo import create_demo_database
from evals.schema_holdout import create_schema_holdout_database


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


class NativeMetadataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)

    def test_read_schema_extracts_adjacent_comments_without_mutation(self) -> None:
        database = self.root / "commented.sqlite3"
        with closing(sqlite3.connect(database)) as connection:
            connection.executescript(
                '''
                CREATE TABLE "order facts" /* 合成订单事实表。 */ (
                    /* 订单稳定标识。 */ "order id" TEXT PRIMARY KEY,
                    amount_cents /* 金额以整数分保存。 */ INTEGER NOT NULL,
                    status -- 原生状态编码。
                        TEXT NOT NULL,
                    note TEXT DEFAULT '/* 字符串不是元数据注释 */',
                    CHECK (status != '-- 也不是注释')
                );
                '''
            )
            connection.commit()
        before = _sha256(database)

        tables = read_schema(database)

        self.assertEqual(_sha256(database), before)
        self.assertEqual(len(tables), 1)
        table = tables[0]
        self.assertEqual(table.name, "order facts")
        self.assertEqual(table.description, "合成订单事实表。")
        descriptions = {column.name: column.description for column in table.columns}
        self.assertEqual(
            descriptions,
            {
                "order id": "订单稳定标识。",
                "amount_cents": "金额以整数分保存。",
                "status": "原生状态编码。",
                "note": None,
            },
        )
        self.assertEqual(table.columns[1].declared_type, "INTEGER")
        self.assertFalse(table.columns[1].nullable)

    def test_schema_without_adjacent_comments_preserves_null_descriptions(self) -> None:
        database = create_demo_database(self.root / "plain.sqlite3")
        before = _sha256(database)

        tables = read_schema(database)

        self.assertEqual(_sha256(database), before)
        self.assertTrue(all(table.description is None for table in tables))
        self.assertTrue(
            all(
                column.description is None
                for table in tables
                for column in table.columns
            )
        )

    def test_builder_prefers_native_descriptions_and_marks_generated_fallback(self) -> None:
        schema = [
            {
                "name": "sales_orders",
                "description": "库内原生订单表说明。",
                "columns": [
                    {
                        "name": "order_id",
                        "declared_type": "TEXT",
                        "primary_key_position": 1,
                        "description": "库内原生订单号说明。",
                    },
                    {
                        "name": "status",
                        "declared_type": "TEXT",
                        "primary_key_position": 0,
                    },
                ],
                "foreign_keys": [],
            }
        ]

        knowledge = build_schema_knowledge(schema)
        notes = {note.reference: note for note in knowledge.field_descriptions}

        self.assertEqual(
            notes["sales_orders.order_id"].table_description,
            "库内原生订单表说明。",
        )
        self.assertEqual(notes["sales_orders.order_id"].table_description_source, "native")
        self.assertEqual(
            notes["sales_orders.order_id"].description,
            "库内原生订单号说明。",
        )
        self.assertEqual(notes["sales_orders.order_id"].description_source, "native")
        self.assertIn("状态编码", notes["sales_orders.status"].description)
        self.assertEqual(notes["sales_orders.status"].description_source, "generated")

    def test_description_merge_has_explicit_native_generated_empty_order(self) -> None:
        self.assertEqual(
            merge_description_layers("native", "generated"),
            ("native", "native"),
        )
        self.assertEqual(
            merge_description_layers(None, "generated"),
            ("generated", "generated"),
        )
        self.assertEqual(merge_description_layers(None, None), (None, "empty"))

    def test_builder_rejects_invalid_native_description_types(self) -> None:
        base = {
            "name": "orders",
            "columns": [
                {
                    "name": "order_id",
                    "declared_type": "TEXT",
                    "primary_key_position": 1,
                }
            ],
            "foreign_keys": [],
        }
        for key, value in (("description", 123), ("column_description", [])):
            invalid = dict(base)
            invalid["columns"] = [dict(base["columns"][0])]
            if key == "description":
                invalid["description"] = value
            else:
                invalid["columns"][0]["description"] = value
            with self.subTest(key=key):
                with self.assertRaises(SchemaKnowledgeError):
                    build_schema_knowledge([invalid])

    def test_holdout_namespace_is_rebuilt_from_native_comments(self) -> None:
        database = create_schema_holdout_database(self.root / "holdout.sqlite3")
        schema = _snapshot(database)
        derived = build_schema_knowledge(schema)
        packaged = load_business_knowledge(SCHEMA_HOLDOUT_DATASOURCE_ID)

        self.assertEqual(len(derived.field_descriptions), 16)
        self.assertTrue(
            all(note.table_description_source == "native" for note in derived.field_descriptions)
        )
        self.assertTrue(
            all(note.description_source == "native" for note in derived.field_descriptions)
        )
        self.assertEqual(
            [(note.reference, note.description) for note in derived.field_descriptions],
            [(note.reference, note.description) for note in packaged.field_descriptions],
        )


if __name__ == "__main__":
    unittest.main()
