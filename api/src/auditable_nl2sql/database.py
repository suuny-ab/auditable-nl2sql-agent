"""SQLite schema inspection and fail-closed read-only query execution."""

from __future__ import annotations

import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .native_metadata import extract_sqlite_ddl_comments


class ReadOnlyViolation(ValueError):
    """Raised when SQL attempts an operation outside the read-only contract."""


class QueryExecutionError(RuntimeError):
    """Raised when an allowed query cannot be executed."""


class QueryTimeoutError(QueryExecutionError):
    """Raised when a query exceeds its local execution deadline."""


@dataclass(frozen=True)
class ColumnSchema:
    name: str
    declared_type: str
    nullable: bool
    primary_key_position: int
    default_value: str | None
    description: str | None = None


@dataclass(frozen=True)
class ForeignKeySchema:
    column: str
    referenced_table: str
    referenced_column: str


@dataclass(frozen=True)
class TableSchema:
    name: str
    columns: tuple[ColumnSchema, ...]
    foreign_keys: tuple[ForeignKeySchema, ...]
    description: str | None = None


@dataclass(frozen=True)
class QueryResult:
    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]
    truncated: bool

    @property
    def returned_row_count(self) -> int:
        return len(self.rows)


_DENIED_ACTION_NAMES = (
    "SQLITE_ALTER_TABLE",
    "SQLITE_ANALYZE",
    "SQLITE_ATTACH",
    "SQLITE_CREATE_INDEX",
    "SQLITE_CREATE_TABLE",
    "SQLITE_CREATE_TEMP_INDEX",
    "SQLITE_CREATE_TEMP_TABLE",
    "SQLITE_CREATE_TEMP_TRIGGER",
    "SQLITE_CREATE_TEMP_VIEW",
    "SQLITE_CREATE_TRIGGER",
    "SQLITE_CREATE_VIEW",
    "SQLITE_CREATE_VTABLE",
    "SQLITE_DELETE",
    "SQLITE_DETACH",
    "SQLITE_DROP_INDEX",
    "SQLITE_DROP_TABLE",
    "SQLITE_DROP_TEMP_INDEX",
    "SQLITE_DROP_TEMP_TABLE",
    "SQLITE_DROP_TEMP_TRIGGER",
    "SQLITE_DROP_TEMP_VIEW",
    "SQLITE_DROP_TRIGGER",
    "SQLITE_DROP_VIEW",
    "SQLITE_DROP_VTABLE",
    "SQLITE_INSERT",
    "SQLITE_PRAGMA",
    "SQLITE_REINDEX",
    "SQLITE_SAVEPOINT",
    "SQLITE_TRANSACTION",
    "SQLITE_UPDATE",
)
_DENIED_ACTIONS = frozenset(
    getattr(sqlite3, name) for name in _DENIED_ACTION_NAMES if hasattr(sqlite3, name)
)


def _read_only_uri(database_path: Path) -> str:
    path = database_path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"SQLite database does not exist: {path}")
    return f"{path.as_uri()}?mode=ro"


def _connect_read_only(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(_read_only_uri(database_path), uri=True)
    connection.execute("PRAGMA query_only = ON")
    return connection


def _deny_mutations(
    action_code: int,
    _argument_one: str | None,
    _argument_two: str | None,
    _database_name: str | None,
    _trigger_name: str | None,
) -> int:
    if action_code in _DENIED_ACTIONS:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def read_schema(database_path: str | Path) -> tuple[TableSchema, ...]:
    """Return user table, column, primary-key, and foreign-key metadata."""

    with closing(_connect_read_only(Path(database_path))) as connection:
        table_definitions = tuple(
            (str(row[0]), None if row[1] is None else str(row[1]))
            for row in connection.execute(
                """
                SELECT name, sql
                FROM sqlite_schema
                WHERE type = 'table' AND name NOT GLOB 'sqlite_*'
                ORDER BY name
                """
            )
        )

        tables: list[TableSchema] = []
        for table_name, create_sql in table_definitions:
            column_rows = connection.execute(
                """
                SELECT name, type, \"notnull\", dflt_value, pk
                FROM pragma_table_info(?)
                ORDER BY cid
                """,
                (table_name,),
            ).fetchall()
            native_metadata = extract_sqlite_ddl_comments(
                create_sql,
                table_name=table_name,
                column_names=tuple(str(row[0]) for row in column_rows),
            )
            columns = tuple(
                ColumnSchema(
                    name=str(row[0]),
                    declared_type=str(row[1]),
                    nullable=not bool(row[2]) and not bool(row[4]),
                    default_value=None if row[3] is None else str(row[3]),
                    primary_key_position=int(row[4]),
                    description=native_metadata.column_descriptions.get(str(row[0])),
                )
                for row in column_rows
            )

            foreign_key_rows = connection.execute(
                """
                SELECT \"from\", \"table\", \"to\"
                FROM pragma_foreign_key_list(?)
                ORDER BY id, seq
                """,
                (table_name,),
            ).fetchall()
            foreign_keys = tuple(
                ForeignKeySchema(
                    column=str(row[0]),
                    referenced_table=str(row[1]),
                    referenced_column=str(row[2]),
                )
                for row in foreign_key_rows
            )
            tables.append(
                TableSchema(
                    name=table_name,
                    columns=columns,
                    foreign_keys=foreign_keys,
                    description=native_metadata.table_description,
                )
            )
        return tuple(tables)


def validate_read_only_statement(
    database_path: str | Path,
    sql: str,
    *,
    timeout_seconds: float = 2.0,
) -> None:
    """Validate one SQL statement without executing its result-producing plan."""

    if not sql.strip():
        raise ValueError("SQL must not be empty")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    deadline = time.monotonic() + timeout_seconds
    with closing(_connect_read_only(Path(database_path))) as connection:
        connection.set_authorizer(_deny_mutations)
        connection.set_progress_handler(
            lambda: int(time.monotonic() >= deadline),
            1_000,
        )
        try:
            connection.execute(f"EXPLAIN QUERY PLAN {sql}").fetchall()
        except sqlite3.DatabaseError as exc:
            message = str(exc).lower()
            if "interrupted" in message:
                raise QueryTimeoutError(
                    "SQL validation exceeded its execution deadline"
                ) from exc
            if (
                "not authorized" in message
                or "readonly" in message
                or "query only" in message
            ):
                raise ReadOnlyViolation(
                    "SQL violates the read-only validation contract"
                ) from exc
            raise QueryExecutionError(
                f"SQLite could not validate the query: {exc}"
            ) from exc
        finally:
            connection.set_progress_handler(None, 0)


def execute_read_only(
    database_path: str | Path,
    sql: str,
    *,
    max_rows: int = 100,
    timeout_seconds: float = 2.0,
) -> QueryResult:
    """Execute one result-producing SQLite statement under hard read-only limits."""

    if not sql.strip():
        raise ValueError("SQL must not be empty")
    if max_rows <= 0:
        raise ValueError("max_rows must be a positive integer")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    deadline = time.monotonic() + timeout_seconds
    with closing(_connect_read_only(Path(database_path))) as connection:
        connection.set_authorizer(_deny_mutations)
        connection.set_progress_handler(
            lambda: int(time.monotonic() >= deadline),
            1_000,
        )
        try:
            cursor = connection.execute(sql)
            if cursor.description is None:
                raise ReadOnlyViolation("SQL must be a result-producing read-only query")
            columns = tuple(item[0] for item in cursor.description)
            fetched = cursor.fetchmany(max_rows + 1)
        except sqlite3.DatabaseError as exc:
            message = str(exc).lower()
            if "interrupted" in message:
                raise QueryTimeoutError("SQL query exceeded its execution deadline") from exc
            if (
                "not authorized" in message
                or "readonly" in message
                or "query only" in message
            ):
                raise ReadOnlyViolation("SQL violates the read-only execution contract") from exc
            raise QueryExecutionError(f"SQLite could not execute the query: {exc}") from exc
        finally:
            connection.set_progress_handler(None, 0)

    truncated = len(fetched) > max_rows
    visible_rows = fetched[:max_rows]
    return QueryResult(
        columns=columns,
        rows=tuple(tuple(row) for row in visible_rows),
        truncated=truncated,
    )
