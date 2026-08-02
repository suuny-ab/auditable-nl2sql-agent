"""Bounded read-only collection of synthetic low-cardinality text values."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .database import QueryExecutionError, execute_read_only, read_schema


VALUE_COLLECTION_SCHEMA_VERSION = "low-cardinality-value-collection-v1"
DEFAULT_MAX_DISTINCT_VALUES = 16
DEFAULT_MAX_CANDIDATE_FIELDS = 32
DEFAULT_MAX_VALUE_CHARS = 256
DEFAULT_VALUE_COLLECTION_TIMEOUT_SECONDS = 2.0
MAX_DISTINCT_VALUES_LIMIT = 64
MAX_CANDIDATE_FIELDS_LIMIT = 128
MAX_VALUE_CHARS_LIMIT = 1_024
MAX_VALUE_COLLECTION_TIMEOUT_SECONDS = 10.0

_EXCLUDED_NAME_TOKENS = frozenset(
    {
        "address",
        "date",
        "day",
        "description",
        "email",
        "id",
        "key",
        "label",
        "name",
        "no",
        "note",
        "number",
        "occurred",
        "phone",
        "sku",
        "text",
        "time",
        "timestamp",
        "title",
        "url",
    }
)


class ValueCollectionError(ValueError):
    """Raised when a bounded value collection cannot be performed safely."""


@dataclass(frozen=True)
class CollectedEnumField:
    table: str
    field: str
    values: tuple[str, ...]

    @property
    def reference(self) -> str:
        return f"{self.table}.{self.field}"


@dataclass(frozen=True)
class LowCardinalityValueCollection:
    schema_version: str
    max_distinct_values: int
    max_candidate_fields: int
    max_value_chars: int
    timeout_seconds: float
    table_names: tuple[str, ...]
    candidate_fields: tuple[str, ...]
    fields: tuple[CollectedEnumField, ...]
    skipped_high_cardinality_fields: tuple[str, ...]
    skipped_unsafe_value_fields: tuple[str, ...]

    @property
    def candidate_field_count(self) -> int:
        return len(self.candidate_fields)

    @property
    def collected_field_count(self) -> int:
        return len(self.fields)


def _bounded_integer(value: object, label: str, maximum: int) -> int:
    if type(value) is not int or value <= 0 or value > maximum:
        raise ValueCollectionError(f"{label} must be an integer from 1 to {maximum}")
    return value


def _bounded_timeout(value: object) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
        or value > MAX_VALUE_COLLECTION_TIMEOUT_SECONDS
    ):
        raise ValueCollectionError(
            "timeout_seconds must be greater than 0 and at most "
            f"{MAX_VALUE_COLLECTION_TIMEOUT_SECONDS}"
        )
    return float(value)


def _identifier_tokens(value: str) -> frozenset[str]:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value)
    return frozenset(
        token
        for token in re.split(r"[^a-z0-9]+", separated.casefold())
        if token
    )


def _has_text_affinity(declared_type: str) -> bool:
    normalized = declared_type.strip().upper()
    return any(marker in normalized for marker in ("CHAR", "CLOB", "TEXT"))


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def collect_low_cardinality_values(
    database_path: str | Path,
    *,
    max_distinct_values: int = DEFAULT_MAX_DISTINCT_VALUES,
    max_candidate_fields: int = DEFAULT_MAX_CANDIDATE_FIELDS,
    max_value_chars: int = DEFAULT_MAX_VALUE_CHARS,
    timeout_seconds: float = DEFAULT_VALUE_COLLECTION_TIMEOUT_SECONDS,
) -> LowCardinalityValueCollection:
    """Collect complete bounded value sets from eligible synthetic text fields.

    The function is an offline governance builder. It reuses the product's
    read-only query sandbox and never returns a truncated prefix as an enum.
    """

    distinct_limit = _bounded_integer(
        max_distinct_values,
        "max_distinct_values",
        MAX_DISTINCT_VALUES_LIMIT,
    )
    field_limit = _bounded_integer(
        max_candidate_fields,
        "max_candidate_fields",
        MAX_CANDIDATE_FIELDS_LIMIT,
    )
    value_char_limit = _bounded_integer(
        max_value_chars,
        "max_value_chars",
        MAX_VALUE_CHARS_LIMIT,
    )
    timeout = _bounded_timeout(timeout_seconds)
    database = Path(database_path)
    tables = read_schema(database)

    candidates: list[tuple[str, str]] = []
    for table in tables:
        foreign_key_fields = {key.column for key in table.foreign_keys}
        for column in table.columns:
            if not _has_text_affinity(column.declared_type):
                continue
            if column.primary_key_position or column.name in foreign_key_fields:
                continue
            if _identifier_tokens(column.name) & _EXCLUDED_NAME_TOKENS:
                continue
            candidates.append((table.name, column.name))
    if len(candidates) > field_limit:
        raise ValueCollectionError(
            "eligible candidate field count exceeds max_candidate_fields"
        )

    collected: list[CollectedEnumField] = []
    skipped_high_cardinality: list[str] = []
    skipped_unsafe_values: list[str] = []
    for table_name, field_name in candidates:
        quoted_table = _quote_identifier(table_name)
        quoted_field = _quote_identifier(field_name)
        sql = (
            f"SELECT DISTINCT {quoted_field} FROM {quoted_table} "
            f"WHERE {quoted_field} IS NOT NULL LIMIT {distinct_limit + 1}"
        )
        try:
            result = execute_read_only(
                database,
                sql,
                max_rows=distinct_limit + 1,
                timeout_seconds=timeout,
            )
        except QueryExecutionError as exc:
            raise ValueCollectionError(
                f"could not collect values for {table_name}.{field_name}"
            ) from exc
        reference = f"{table_name}.{field_name}"
        if result.truncated or len(result.rows) > distinct_limit:
            skipped_high_cardinality.append(reference)
            continue

        values: list[str] = []
        normalized_values: set[str] = set()
        unsafe = False
        for row in result.rows:
            if len(row) != 1 or not isinstance(row[0], str):
                unsafe = True
                break
            value = row[0]
            if not value.strip():
                continue
            if value != value.strip() or len(value) > value_char_limit:
                unsafe = True
                break
            normalized = value.casefold()
            if normalized in normalized_values:
                unsafe = True
                break
            normalized_values.add(normalized)
            values.append(value)
        if unsafe:
            skipped_unsafe_values.append(reference)
            continue
        if values:
            values.sort(key=lambda value: (value.casefold(), value))
            collected.append(
                CollectedEnumField(
                    table=table_name,
                    field=field_name,
                    values=tuple(values),
                )
            )

    return LowCardinalityValueCollection(
        schema_version=VALUE_COLLECTION_SCHEMA_VERSION,
        max_distinct_values=distinct_limit,
        max_candidate_fields=field_limit,
        max_value_chars=value_char_limit,
        timeout_seconds=timeout,
        table_names=tuple(table.name for table in tables),
        candidate_fields=tuple(
            f"{table_name}.{field_name}" for table_name, field_name in candidates
        ),
        fields=tuple(collected),
        skipped_high_cardinality_fields=tuple(skipped_high_cardinality),
        skipped_unsafe_value_fields=tuple(skipped_unsafe_values),
    )


def build_enum_values_payload(
    collection: LowCardinalityValueCollection,
) -> dict[str, Any]:
    """Project one collection into the packaged enum-values-v1 JSON contract."""

    if not isinstance(collection, LowCardinalityValueCollection):
        raise ValueCollectionError("collection must be a LowCardinalityValueCollection")
    fields_by_table: dict[str, list[CollectedEnumField]] = {
        table_name: [] for table_name in collection.table_names
    }
    for field in collection.fields:
        if field.table not in fields_by_table:
            raise ValueCollectionError("collected field references an unknown table")
        fields_by_table[field.table].append(field)
    return {
        "schema_version": "enum-values-v1",
        "tables": [
            {
                "name": table_name,
                "fields": [
                    {
                        "name": field.field,
                        "values": [
                            {"value": value, "aliases": []}
                            for value in field.values
                        ],
                    }
                    for field in fields_by_table[table_name]
                ],
            }
            for table_name in collection.table_names
        ],
    }
