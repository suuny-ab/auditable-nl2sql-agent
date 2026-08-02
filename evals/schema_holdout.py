"""Frozen alternate-schema fixture and contract for one generalization baseline."""

from __future__ import annotations

import argparse
import re
import sqlite3
from collections import Counter
from collections.abc import Iterable, Mapping
from contextlib import closing
from pathlib import Path
from typing import Any

from evals.contract import load_cases, validate_case_contract


SCHEMA_HOLDOUT_CASE_SCHEMA_VERSION = "schema-holdout-case-v1"
SCHEMA_HOLDOUT_CONTRACT_NAME = "schema-holdout-v1"
SCHEMA_HOLDOUT_CASE_IDS = (
    "success-001",
    "success-004",
    "success-005",
    "success-006",
    "success-007",
    "success-013",
    "success-016",
    "ambiguity-003",
    "ambiguity-004",
    "no_answer-002",
    "no_answer-003",
    "unauthorized-001",
    "unauthorized-005",
    "injection-001",
    "injection-005",
)
SCHEMA_HOLDOUT_CATEGORY_COUNTS = {
    "success": 7,
    "ambiguity": 2,
    "no_answer": 2,
    "unauthorized": 2,
    "injection": 2,
}
SCHEMA_HOLDOUT_REFERENCE_CASE_IDS = frozenset(
    {
        "success-001",
        "success-004",
        "success-005",
        "success-006",
        "success-007",
        "success-013",
        "success-016",
        "unauthorized-001",
    }
)
SCHEMA_HOLDOUT_TABLE_COLUMNS = {
    "buyer_directory": (
        "buyer_key",
        "buyer_label",
        "market_area",
        "buyer_class",
    ),
    "merchandise": (
        "sku",
        "title",
        "department",
        "catalog_price_cents",
    ),
    "transaction_lines": (
        "ticket_no",
        "buyer_key",
        "sku",
        "occurred_on",
        "state_code",
        "source_code",
        "units",
        "paid_unit_cents",
    ),
}
MAIN_TABLE_NAMES = frozenset({"customers", "products", "orders", "order_items"})
MAIN_COLUMN_NAMES = frozenset(
    {
        "customer_id",
        "customer_name",
        "region",
        "segment",
        "product_id",
        "product_name",
        "category",
        "list_price",
        "order_id",
        "order_date",
        "status",
        "sales_channel",
        "quantity",
        "unit_price",
    }
)

_CASE_KEYS = {
    "schema_version",
    "case_id",
    "category",
    "question",
    "reference_sql",
    "expected",
}
_NEW_TABLE_PATTERN = re.compile(
    r"\b(?:buyer_directory|merchandise|transaction_lines)\b",
    re.IGNORECASE,
)
_MAIN_TABLE_PATTERN = re.compile(
    r"\b(?:customers|products|orders|order_items)\b",
    re.IGNORECASE,
)

_SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE buyer_directory /* 合成客户主数据；buyer 表示客户。 */ (
    buyer_key /* 客户唯一标识。 */ TEXT PRIMARY KEY,
    buyer_label /* 客户展示名称。 */ TEXT NOT NULL,
    market_area /* 客户所属地区，对应区域。 */ TEXT NOT NULL,
    buyer_class /* 客户业务分群。 */ TEXT NOT NULL
);

CREATE TABLE merchandise /* 合成商品主数据。 */ (
    sku /* 商品唯一标识。 */ TEXT PRIMARY KEY,
    title /* 商品展示名称。 */ TEXT NOT NULL,
    department /* 商品所属品类。 */ TEXT NOT NULL,
    catalog_price_cents /* 商品目录标价，以整数分保存。 */ INTEGER NOT NULL CHECK (catalog_price_cents >= 0)
);

CREATE TABLE transaction_lines /* 合成订单商品明细事实表。 */ (
    ticket_no /* 订单唯一标识；同一订单可有多条商品明细。 */ TEXT NOT NULL,
    buyer_key /* 客户标识，关联客户主数据。 */ TEXT NOT NULL REFERENCES buyer_directory(buyer_key),
    sku /* 商品标识，关联商品主数据。 */ TEXT NOT NULL REFERENCES merchandise(sku),
    occurred_on /* 订单日期，格式为 YYYY-MM-DD。 */ TEXT NOT NULL,
    state_code /* 订单状态：SETTLED=paid，IN_TRANSIT=shipped，CLOSED=completed，VOID=cancelled。 */ TEXT NOT NULL CHECK (
        state_code IN ('SETTLED', 'IN_TRANSIT', 'CLOSED', 'VOID')
    ),
    source_code /* 销售渠道：WEB=online，SHOP=store，PLATFORM=marketplace。 */ TEXT NOT NULL CHECK (
        source_code IN ('WEB', 'SHOP', 'PLATFORM')
    ),
    units /* 订单行购买数量。 */ INTEGER NOT NULL CHECK (units > 0),
    paid_unit_cents /* 实际成交单价，以整数分保存；计算销售额后除以 100 换算元。 */ INTEGER NOT NULL CHECK (paid_unit_cents >= 0),
    PRIMARY KEY (ticket_no, sku)
);
"""

_BUYERS = (
    ("C001", "星河户外（合成）", "华东", "企业"),
    ("C002", "云杉生活（合成）", "华南", "零售"),
    ("C003", "蓝鲸数码（合成）", "华北", "零售"),
    ("C004", "晨光办公（合成）", "西南", "企业"),
)
_MERCHANDISE = (
    ("P101", "徒步背包", "户外", 39900),
    ("P102", "保温杯", "家居", 12900),
    ("P103", "蓝牙耳机", "数码", 29900),
    ("P104", "机械键盘", "数码", 49900),
    ("P105", "显示器支架", "办公", 25900),
)
_TRANSACTION_LINES = (
    ("O1001", "C001", "P101", "2026-01-05", "CLOSED", "WEB", 2, 39900),
    ("O1001", "C001", "P102", "2026-01-05", "CLOSED", "WEB", 3, 12900),
    ("O1002", "C002", "P102", "2026-01-18", "CLOSED", "SHOP", 5, 12500),
    ("O1002", "C002", "P105", "2026-01-18", "CLOSED", "SHOP", 1, 25900),
    ("O1003", "C003", "P103", "2026-02-02", "VOID", "WEB", 2, 29900),
    ("O1004", "C001", "P101", "2026-02-20", "CLOSED", "PLATFORM", 1, 38900),
    ("O1004", "C001", "P103", "2026-02-20", "CLOSED", "PLATFORM", 2, 28900),
    ("O1005", "C004", "P104", "2026-03-03", "SETTLED", "WEB", 3, 47900),
    ("O1005", "C004", "P105", "2026-03-03", "SETTLED", "WEB", 2, 24900),
    ("O1006", "C002", "P102", "2026-03-16", "IN_TRANSIT", "PLATFORM", 4, 11900),
    ("O1006", "C002", "P104", "2026-03-16", "IN_TRANSIT", "PLATFORM", 1, 49900),
)


class SchemaHoldoutContractError(ValueError):
    """Raised when the alternate fixture or mapped HOLDOUT drifts."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SchemaHoldoutContractError(message)


def create_schema_holdout_database(database_path: str | Path) -> Path:
    """Create the alternate synthetic database without overwriting evidence."""

    path = Path(database_path).resolve()
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing database: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with closing(sqlite3.connect(path)) as connection:
            connection.executescript(_SCHEMA_SQL)
            connection.executemany(
                "INSERT INTO buyer_directory VALUES (?, ?, ?, ?)",
                _BUYERS,
            )
            connection.executemany(
                "INSERT INTO merchandise VALUES (?, ?, ?, ?)",
                _MERCHANDISE,
            )
            connection.executemany(
                "INSERT INTO transaction_lines VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                _TRANSACTION_LINES,
            )
            connection.commit()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


def validate_schema_holdout_contract(
    cases: Iterable[Mapping[str, Any]],
) -> None:
    """Validate exact source mapping while keeping the original 40-case contract intact."""

    materialized = list(cases)
    source_cases = load_cases(Path(__file__).with_name("cases.jsonl"))
    validate_case_contract(source_cases)
    source_by_id = {case["case_id"]: case for case in source_cases}

    _require(len(materialized) == 15, "schema HOLDOUT must contain exactly 15 cases")
    _require(
        all(isinstance(case, Mapping) for case in materialized),
        "schema HOLDOUT cases must be objects",
    )
    _require(
        [case["case_id"] for case in materialized] == list(SCHEMA_HOLDOUT_CASE_IDS),
        "schema HOLDOUT case order or IDs changed",
    )
    categories: list[str] = []
    questions: list[str] = []
    for index, case in enumerate(materialized, start=1):
        _require(set(case) == _CASE_KEYS, f"case {index}: fields changed")
        _require(
            case["schema_version"] == SCHEMA_HOLDOUT_CASE_SCHEMA_VERSION,
            f"case {index}: unsupported schema version",
        )
        case_id = case["case_id"]
        source = source_by_id[case_id]
        _require(case["category"] == source["category"], f"{case_id}: category drifted")
        _require(case["question"] == source["question"], f"{case_id}: question drifted")
        _require(case["expected"] == source["expected"], f"{case_id}: expected drifted")

        reference_sql = case["reference_sql"]
        if case_id in SCHEMA_HOLDOUT_REFERENCE_CASE_IDS:
            _require(
                isinstance(reference_sql, str)
                and reference_sql == reference_sql.strip()
                and bool(reference_sql),
                f"{case_id}: mapped reference SQL is required",
            )
            _require(
                reference_sql != source["reference_sql"],
                f"{case_id}: mapped reference SQL was copied from the main schema",
            )
            _require(
                _NEW_TABLE_PATTERN.search(reference_sql) is not None,
                f"{case_id}: mapped reference SQL does not use the alternate schema",
            )
            _require(
                _MAIN_TABLE_PATTERN.search(reference_sql) is None,
                f"{case_id}: mapped reference SQL references a main-schema table",
            )
        else:
            _require(reference_sql is None, f"{case_id}: reference SQL must be null")
        categories.append(case["category"])
        questions.append(case["question"])

    _require(len(set(questions)) == 15, "schema HOLDOUT questions must be unique")
    _require(
        Counter(categories) == Counter(SCHEMA_HOLDOUT_CATEGORY_COUNTS),
        "schema HOLDOUT category counts must remain 7/2/2/2/2",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the frozen alternate-schema synthetic database."
    )
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    created = create_schema_holdout_database(arguments.output)
    print(f"created={created}")


if __name__ == "__main__":
    main()
