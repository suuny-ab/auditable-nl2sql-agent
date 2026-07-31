from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from auditable_nl2sql.database import (
    QueryExecutionError,
    ReadOnlyViolation,
    execute_read_only,
    read_schema,
)
from auditable_nl2sql.demo import create_demo_database


class ReadOnlyDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.database_path = create_demo_database(
            Path(self.temporary_directory.name) / "sales.sqlite3"
        )

    def _order_count(self) -> int:
        with closing(sqlite3.connect(self.database_path)) as connection:
            return int(connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0])

    def test_schema_reader_returns_four_user_tables_with_keys(self) -> None:
        schema = read_schema(self.database_path)

        self.assertEqual(
            [table.name for table in schema],
            ["customers", "order_items", "orders", "products"],
        )
        orders = next(table for table in schema if table.name == "orders")
        self.assertEqual(orders.columns[0].name, "order_id")
        self.assertEqual(orders.columns[0].primary_key_position, 1)
        self.assertFalse(orders.columns[0].nullable)
        self.assertEqual(
            [(key.column, key.referenced_table, key.referenced_column) for key in orders.foreign_keys],
            [("customer_id", "customers", "customer_id")],
        )

    def test_read_only_query_returns_deterministic_revenue(self) -> None:
        result = execute_read_only(
            self.database_path,
            """
            SELECT ROUND(SUM(item.quantity * item.unit_price), 2) AS revenue
            FROM order_items AS item
            JOIN orders AS sales_order USING (order_id)
            WHERE sales_order.status != 'cancelled'
            """,
        )

        self.assertEqual(result.columns, ("revenue",))
        self.assertEqual(result.rows, ((5946.0,),))
        self.assertFalse(result.truncated)

    def test_demo_database_has_deterministic_table_counts(self) -> None:
        result = execute_read_only(
            self.database_path,
            """
            SELECT 'customers' AS table_name, COUNT(*) AS row_count FROM customers
            UNION ALL SELECT 'products', COUNT(*) FROM products
            UNION ALL SELECT 'orders', COUNT(*) FROM orders
            UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
            """,
        )

        self.assertEqual(
            result.rows,
            (
                ("customers", 4),
                ("products", 5),
                ("orders", 6),
                ("order_items", 11),
            ),
        )

    def test_row_limit_truncates_visible_result(self) -> None:
        result = execute_read_only(
            self.database_path,
            "SELECT order_id FROM orders ORDER BY order_id",
            max_rows=2,
        )

        self.assertEqual(result.rows, (("O1001",), ("O1002",)))
        self.assertEqual(result.returned_row_count, 2)
        self.assertTrue(result.truncated)

    def test_mutating_and_privileged_statements_are_denied_without_changes(self) -> None:
        original_count = self._order_count()
        rejected_sql = (
            "INSERT INTO orders VALUES ('O9999', 'C001', '2026-03-31', 'paid', 'online')",
            "UPDATE orders SET status = 'cancelled' WHERE order_id = 'O1001'",
            "DELETE FROM orders WHERE order_id = 'O1001'",
            "CREATE TABLE leaked (value TEXT)",
            "DROP TABLE products",
            "ATTACH DATABASE ':memory:' AS other",
            "PRAGMA schema_version",
        )

        for sql in rejected_sql:
            with self.subTest(sql=sql):
                with self.assertRaises(ReadOnlyViolation):
                    execute_read_only(self.database_path, sql)

        self.assertEqual(self._order_count(), original_count)
        self.assertEqual(
            [table.name for table in read_schema(self.database_path)],
            ["customers", "order_items", "orders", "products"],
        )

    def test_multiple_statements_fail_closed(self) -> None:
        with self.assertRaises(QueryExecutionError):
            execute_read_only(
                self.database_path,
                "SELECT 1; SELECT 2",
            )

    def test_demo_database_refuses_to_overwrite(self) -> None:
        with self.assertRaises(FileExistsError):
            create_demo_database(self.database_path)

    def test_invalid_limits_are_rejected_before_execution(self) -> None:
        with self.assertRaises(ValueError):
            execute_read_only(self.database_path, "SELECT 1", max_rows=0)
        with self.assertRaises(ValueError):
            execute_read_only(self.database_path, "SELECT 1", timeout_seconds=0)


if __name__ == "__main__":
    unittest.main()
