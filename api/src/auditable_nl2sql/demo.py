"""Create the deterministic synthetic e-commerce SQLite database."""

from __future__ import annotations

import argparse
import sqlite3
from contextlib import closing
from pathlib import Path


_SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    region TEXT NOT NULL,
    segment TEXT NOT NULL
);

CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    list_price REAL NOT NULL CHECK (list_price >= 0)
);

CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    order_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('paid', 'shipped', 'completed', 'cancelled')),
    sales_channel TEXT NOT NULL
);

CREATE TABLE order_items (
    order_id TEXT NOT NULL REFERENCES orders(order_id),
    product_id TEXT NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL NOT NULL CHECK (unit_price >= 0),
    PRIMARY KEY (order_id, product_id)
);
"""

_CUSTOMERS = (
    ("C001", "星河户外（合成）", "华东", "企业"),
    ("C002", "云杉生活（合成）", "华南", "零售"),
    ("C003", "蓝鲸数码（合成）", "华北", "零售"),
    ("C004", "晨光办公（合成）", "西南", "企业"),
)

_PRODUCTS = (
    ("P101", "徒步背包", "户外", 399.0),
    ("P102", "保温杯", "家居", 129.0),
    ("P103", "蓝牙耳机", "数码", 299.0),
    ("P104", "机械键盘", "数码", 499.0),
    ("P105", "显示器支架", "办公", 259.0),
)

_ORDERS = (
    ("O1001", "C001", "2026-01-05", "completed", "online"),
    ("O1002", "C002", "2026-01-18", "completed", "store"),
    ("O1003", "C003", "2026-02-02", "cancelled", "online"),
    ("O1004", "C001", "2026-02-20", "completed", "marketplace"),
    ("O1005", "C004", "2026-03-03", "paid", "online"),
    ("O1006", "C002", "2026-03-16", "shipped", "marketplace"),
)

_ORDER_ITEMS = (
    ("O1001", "P101", 2, 399.0),
    ("O1001", "P102", 3, 129.0),
    ("O1002", "P102", 5, 125.0),
    ("O1002", "P105", 1, 259.0),
    ("O1003", "P103", 2, 299.0),
    ("O1004", "P101", 1, 389.0),
    ("O1004", "P103", 2, 289.0),
    ("O1005", "P104", 3, 479.0),
    ("O1005", "P105", 2, 249.0),
    ("O1006", "P102", 4, 119.0),
    ("O1006", "P104", 1, 499.0),
)


def create_demo_database(database_path: str | Path) -> Path:
    """Create a new synthetic database without overwriting an existing file."""

    path = Path(database_path).resolve()
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing database: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with closing(sqlite3.connect(path)) as connection:
            connection.executescript(_SCHEMA_SQL)
            connection.executemany(
                "INSERT INTO customers VALUES (?, ?, ?, ?)",
                _CUSTOMERS,
            )
            connection.executemany(
                "INSERT INTO products VALUES (?, ?, ?, ?)",
                _PRODUCTS,
            )
            connection.executemany(
                "INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
                _ORDERS,
            )
            connection.executemany(
                "INSERT INTO order_items VALUES (?, ?, ?, ?)",
                _ORDER_ITEMS,
            )
            connection.commit()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the auditable NL2SQL synthetic demo database."
    )
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    created = create_demo_database(arguments.output)
    print(f"created={created}")


if __name__ == "__main__":
    main()
