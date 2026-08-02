"""Compact deterministic projection of schema metadata for Provider context."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


SCHEMA_SUMMARY_SCHEMA_VERSION = "schema-summary-v1"
_MAX_TABLES = 64
_MAX_COLUMNS = 512
_MAX_IDENTIFIER_CHARS = 256
_MAX_DECLARED_TYPE_CHARS = 128
_MAX_SUMMARY_CHARS = 30_000


class SchemaSummaryError(ValueError):
    """Raised when schema metadata cannot be projected safely."""


def _require_text(value: object, label: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaSummaryError(f"{label} must be non-empty text")
    if len(value) > maximum:
        raise SchemaSummaryError(f"{label} is too long")
    return value


def _declared_type(value: object, label: str) -> str:
    if value is None:
        return "UNDECLARED"
    if not isinstance(value, str):
        raise SchemaSummaryError(f"{label} must be text")
    normalized = value.strip().upper() or "UNDECLARED"
    if len(normalized) > _MAX_DECLARED_TYPE_CHARS:
        raise SchemaSummaryError(f"{label} is too long")
    return normalized


def _primary_key_position(value: object, label: str) -> int:
    if value is None:
        return 0
    if type(value) is not int or value < 0:
        raise SchemaSummaryError(f"{label} must be a non-negative integer")
    return value


def _quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def build_schema_summary(
    schema_snapshot: list[dict[str, Any]],
) -> dict[str, int | str]:
    """Return a bounded table/column/type/key summary without reading row data."""

    if not isinstance(schema_snapshot, list) or not schema_snapshot:
        raise SchemaSummaryError("schema snapshot must be a non-empty list")
    if len(schema_snapshot) > _MAX_TABLES:
        raise SchemaSummaryError("schema snapshot has too many tables")

    tables: dict[str, dict[str, Any]] = {}
    casefolded_table_names: set[str] = set()
    total_columns = 0
    for table_index, table in enumerate(schema_snapshot):
        if not isinstance(table, Mapping):
            raise SchemaSummaryError("schema table must be an object")
        table_name = _require_text(
            table.get("name"),
            f"schema table {table_index} name",
            maximum=_MAX_IDENTIFIER_CHARS,
        )
        if table_name.casefold() in casefolded_table_names:
            raise SchemaSummaryError("schema table names must be unique")
        casefolded_table_names.add(table_name.casefold())

        raw_columns = table.get("columns")
        if not isinstance(raw_columns, list) or not raw_columns:
            raise SchemaSummaryError(f"{table_name}.columns must be a non-empty list")
        total_columns += len(raw_columns)
        if total_columns > _MAX_COLUMNS:
            raise SchemaSummaryError("schema snapshot has too many columns")

        columns: dict[str, tuple[str, int]] = {}
        casefolded_column_names: set[str] = set()
        primary_key_positions: set[int] = set()
        for column_index, column in enumerate(raw_columns):
            if not isinstance(column, Mapping):
                raise SchemaSummaryError("schema column must be an object")
            column_name = _require_text(
                column.get("name"),
                f"{table_name} column {column_index} name",
                maximum=_MAX_IDENTIFIER_CHARS,
            )
            if column_name.casefold() in casefolded_column_names:
                raise SchemaSummaryError(f"{table_name} column names must be unique")
            casefolded_column_names.add(column_name.casefold())
            declared_type = _declared_type(
                column.get("declared_type"),
                f"{table_name}.{column_name} declared type",
            )
            primary_key_position = _primary_key_position(
                column.get("primary_key_position"),
                f"{table_name}.{column_name} primary key position",
            )
            if primary_key_position:
                if primary_key_position in primary_key_positions:
                    raise SchemaSummaryError(
                        f"{table_name} primary key positions must be unique"
                    )
                primary_key_positions.add(primary_key_position)
            columns[column_name] = (declared_type, primary_key_position)
        if primary_key_positions and primary_key_positions != set(
            range(1, len(primary_key_positions) + 1)
        ):
            raise SchemaSummaryError(
                f"{table_name} primary key positions must be contiguous"
            )

        foreign_keys = table.get("foreign_keys", [])
        if not isinstance(foreign_keys, list):
            raise SchemaSummaryError(f"{table_name}.foreign_keys must be a list")
        tables[table_name] = {
            "columns": columns,
            "foreign_keys": foreign_keys,
        }

    lines: list[str] = []
    for table_name in sorted(tables, key=lambda item: (item.casefold(), item)):
        table = tables[table_name]
        columns = table["columns"]
        column_tokens: list[str] = []
        for column_name in sorted(columns, key=lambda item: (item.casefold(), item)):
            declared_type, primary_key_position = columns[column_name]
            token = f"{_quoted(column_name)}:{_quoted(declared_type)}"
            if primary_key_position:
                token += f":pk{primary_key_position}"
            column_tokens.append(token)

        foreign_key_tokens: list[str] = []
        seen_foreign_keys: set[tuple[str, str, str]] = set()
        for foreign_key in table["foreign_keys"]:
            if not isinstance(foreign_key, Mapping):
                raise SchemaSummaryError("schema foreign key must be an object")
            column_name = _require_text(
                foreign_key.get("column"),
                f"{table_name} foreign key column",
                maximum=_MAX_IDENTIFIER_CHARS,
            )
            referenced_table = _require_text(
                foreign_key.get("referenced_table"),
                f"{table_name}.{column_name} referenced table",
                maximum=_MAX_IDENTIFIER_CHARS,
            )
            referenced_column = _require_text(
                foreign_key.get("referenced_column"),
                f"{table_name}.{column_name} referenced column",
                maximum=_MAX_IDENTIFIER_CHARS,
            )
            key = (column_name, referenced_table, referenced_column)
            if key in seen_foreign_keys:
                raise SchemaSummaryError("schema foreign keys must be unique")
            seen_foreign_keys.add(key)
            if column_name not in columns:
                raise SchemaSummaryError("schema foreign key column does not exist")
            referenced = tables.get(referenced_table)
            if referenced is None or referenced_column not in referenced["columns"]:
                raise SchemaSummaryError("schema foreign key target does not exist")
            foreign_key_tokens.append(
                f"{_quoted(column_name)}->{_quoted(referenced_table)}."
                f"{_quoted(referenced_column)}"
            )
        foreign_key_tokens.sort()

        line = f"{_quoted(table_name)}({','.join(column_tokens)})"
        if foreign_key_tokens:
            line += f";fk({','.join(foreign_key_tokens)})"
        lines.append(line)

    text = "\n".join(lines)
    if len(text) > _MAX_SUMMARY_CHARS:
        raise SchemaSummaryError("schema summary is too long")
    return {
        "schema_version": SCHEMA_SUMMARY_SCHEMA_VERSION,
        "table_count": len(tables),
        "column_count": total_columns,
        "text": text,
    }
