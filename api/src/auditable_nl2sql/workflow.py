"""Deterministic LangGraph workflow with persistent, auditable run projection."""

from __future__ import annotations

import json
import math
import operator
import re
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any, Protocol, TypedDict

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .database import (
    QueryExecutionError,
    QueryTimeoutError,
    ReadOnlyViolation,
    execute_read_only,
    read_schema,
    validate_read_only_statement,
)


CANONICAL_QUESTION = "2026年第一季度非取消订单销售额是多少？"
CANONICAL_SQL = (
    "SELECT ROUND(SUM(item.quantity * item.unit_price), 2) AS revenue "
    "FROM order_items AS item "
    "JOIN orders AS sales_order USING (order_id) "
    "WHERE sales_order.status != 'cancelled' "
    "AND sales_order.order_date >= '2026-01-01' "
    "AND sales_order.order_date < '2026-04-01'"
)
RUN_RECORD_SCHEMA_VERSION = "run-record-v2"
DEFAULT_APPROVAL_ROW_LIMIT = 5


class DuplicateRunError(ValueError):
    """Raised when a caller attempts to overwrite an existing run ID."""


class RunNotFoundError(LookupError):
    """Raised when a requested run ID has no persisted checkpoint."""


class InvalidApprovalDecisionError(ValueError):
    """Raised when a decision cannot be applied to a pending run."""


class UnsupportedQuestionError(ValueError):
    """Raised by deterministic generators for questions outside their mapping."""


class UnsupportedResultType(TypeError):
    """Raised when SQLite returns a value outside the JSON trajectory contract."""


class SqlGenerator(Protocol):
    def generate(self, question: str, schema_snapshot: list[dict[str, Any]]) -> str:
        """Return SQL for a question and schema snapshot."""


class StaticSqlGenerator:
    """Deterministic test substitute; it is not an NL2SQL model."""

    def __init__(self, mapping: Mapping[str, str] | None = None) -> None:
        self._mapping = dict(mapping or {CANONICAL_QUESTION: CANONICAL_SQL})

    def generate(self, question: str, schema_snapshot: list[dict[str, Any]]) -> str:
        del schema_snapshot
        try:
            return self._mapping[question]
        except KeyError as exc:
            raise UnsupportedQuestionError("question is outside the deterministic stub") from exc


class TrajectoryEvent(TypedDict):
    sequence: int
    node: str
    status: str
    details: dict[str, Any]


class WorkflowState(TypedDict, total=False):
    run_id: str
    question: str
    schema_snapshot: list[dict[str, Any]]
    generated_sql: str
    query_columns: list[str]
    query_rows: list[list[Any]]
    truncated: bool
    status: str
    error_code: str | None
    error_message: str | None
    attempt_count: int
    approval_required: bool
    approval_reason: str | None
    approval_threshold: int | None
    approval_requested_row_limit: int | None
    approval_can_execute: bool
    approval_decision: str | None
    approval_decision_id: str | None
    trajectory: Annotated[list[TrajectoryEvent], operator.add]


_RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
_DECISION_ID_PATTERN = _RUN_ID_PATTERN
_SIMPLE_LIMIT_PATTERN = re.compile(
    r"\bLIMIT\s+(\d+)(?:\s+OFFSET\s+\d+)?\s*;?\s*\Z",
    re.IGNORECASE,
)
_SINGLE_ROW_AGGREGATE_PATTERN = re.compile(
    r"\b(?:COUNT|SUM|AVG|MIN|MAX)\s*\(",
    re.IGNORECASE,
)
_MULTI_ROW_AGGREGATE_PATTERN = re.compile(
    r"\b(?:GROUP\s+BY|UNION|INTERSECT|EXCEPT)\b",
    re.IGNORECASE,
)


def _event(
    state: WorkflowState,
    *,
    node: str,
    status: str,
    details: dict[str, Any],
) -> TrajectoryEvent:
    return {
        "sequence": len(state.get("trajectory", [])) + 1,
        "node": node,
        "status": status,
        "details": details,
    }


def _failure(
    state: WorkflowState,
    *,
    node: str,
    code: str,
    message: str,
    attempt_count: int | None = None,
) -> dict[str, Any]:
    update: dict[str, Any] = {
        "status": "failed",
        "error_code": code,
        "error_message": message,
        "trajectory": [
            _event(
                state,
                node=node,
                status="failed",
                details={"error_code": code, "error_message": message},
            )
        ],
    }
    if attempt_count is not None:
        update["attempt_count"] = attempt_count
    return update


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
                    "column": foreign_key.column,
                    "referenced_table": foreign_key.referenced_table,
                    "referenced_column": foreign_key.referenced_column,
                }
                for foreign_key in table.foreign_keys
            ],
        }
        for table in read_schema(database_path)
    ]


def _json_scalar(value: Any) -> str | int | float | bool | None:
    if isinstance(value, float) and not math.isfinite(value):
        raise UnsupportedResultType("non-finite floats are not valid JSON values")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise UnsupportedResultType(f"unsupported SQLite result type: {type(value).__name__}")


def _approval_requirement(
    *,
    business_database: Path,
    sql: str,
    row_limit: int,
) -> dict[str, Any] | None:
    try:
        validate_read_only_statement(business_database, sql)
    except ReadOnlyViolation:
        return {
            "reason": "read_only_violation",
            "threshold": row_limit,
            "requested_row_limit": None,
            "can_execute": False,
        }
    except QueryExecutionError:
        # Preserve the execution node as the single source of persisted query errors.
        return None

    limit_match = _SIMPLE_LIMIT_PATTERN.search(sql)
    if limit_match is not None:
        requested_row_limit = int(limit_match.group(1))
        if requested_row_limit <= row_limit:
            return None
        return {
            "reason": "row_limit_exceeded",
            "threshold": row_limit,
            "requested_row_limit": requested_row_limit,
            "can_execute": True,
        }

    if _SINGLE_ROW_AGGREGATE_PATTERN.search(sql) and not (
        _MULTI_ROW_AGGREGATE_PATTERN.search(sql)
    ):
        return None

    return {
        "reason": "row_limit_unbounded",
        "threshold": row_limit,
        "requested_row_limit": None,
        "can_execute": True,
    }


def _build_graph(
    *,
    business_database: Path,
    generator: SqlGenerator,
    approval_row_limit: int,
    checkpointer: SqliteSaver,
):
    def load_schema(state: WorkflowState) -> dict[str, Any]:
        try:
            snapshot = _schema_snapshot(business_database)
        except (OSError, sqlite3.DatabaseError):
            return _failure(
                state,
                node="load_schema",
                code="schema_unavailable",
                message="business database schema is unavailable",
            )
        return {
            "schema_snapshot": snapshot,
            "status": "schema_ready",
            "trajectory": [
                _event(
                    state,
                    node="load_schema",
                    status="completed",
                    details={"table_count": len(snapshot)},
                )
            ],
        }

    def draft_sql(state: WorkflowState) -> dict[str, Any]:
        try:
            sql = generator.generate(state["question"], state["schema_snapshot"])
        except UnsupportedQuestionError:
            return _failure(
                state,
                node="draft_sql",
                code="unsupported_question",
                message="question is outside the deterministic SQL stub",
            )
        except Exception:
            return _failure(
                state,
                node="draft_sql",
                code="generator_error",
                message="SQL generator failed",
            )
        if not isinstance(sql, str) or not sql.strip():
            return _failure(
                state,
                node="draft_sql",
                code="generator_error",
                message="SQL generator returned an empty statement",
            )
        return {
            "generated_sql": sql,
            "status": "sql_ready",
            "trajectory": [
                _event(
                    state,
                    node="draft_sql",
                    status="completed",
                    details={"sql": sql},
                )
            ],
        }

    def assess_sql(state: WorkflowState) -> dict[str, Any]:
        requirement = _approval_requirement(
            business_database=business_database,
            sql=state["generated_sql"],
            row_limit=approval_row_limit,
        )
        if requirement is None:
            return {
                "approval_required": False,
                "approval_reason": None,
                "approval_threshold": approval_row_limit,
                "approval_requested_row_limit": None,
                "approval_can_execute": True,
                "approval_decision": None,
                "approval_decision_id": None,
                "status": "execution_ready",
                "trajectory": [
                    _event(
                        state,
                        node="assess_sql",
                        status="completed",
                        details={"approval_required": False},
                    )
                ],
            }
        return {
            "approval_required": True,
            "approval_reason": requirement["reason"],
            "approval_threshold": requirement["threshold"],
            "approval_requested_row_limit": requirement["requested_row_limit"],
            "approval_can_execute": requirement["can_execute"],
            "approval_decision": None,
            "approval_decision_id": None,
            "status": "pending_approval",
            "trajectory": [
                _event(
                    state,
                    node="assess_sql",
                    status="pending",
                    details={
                        "reason": requirement["reason"],
                        "threshold": requirement["threshold"],
                        "requested_row_limit": requirement["requested_row_limit"],
                        "can_execute": requirement["can_execute"],
                    },
                )
            ],
        }

    def approval_gate(state: WorkflowState) -> dict[str, Any]:
        decision = interrupt(
            {
                "kind": "approval_required",
                "run_id": state["run_id"],
                "sql": state["generated_sql"],
                "reason": state["approval_reason"],
                "threshold": state["approval_threshold"],
                "requested_row_limit": state["approval_requested_row_limit"],
                "can_execute": state["approval_can_execute"],
            }
        )
        approved = decision["approved"]
        decision_id = decision["decision_id"]
        decision_name = "approved" if approved else "rejected"

        if not approved:
            return {
                "approval_decision": decision_name,
                "approval_decision_id": decision_id,
                "status": "rejected",
                "error_code": "approval_rejected",
                "error_message": "query was rejected by human approval",
                "trajectory": [
                    _event(
                        state,
                        node="approval_gate",
                        status="rejected",
                        details={
                            "decision": decision_name,
                            "decision_id": decision_id,
                        },
                    )
                ],
            }

        if not state["approval_can_execute"]:
            return {
                "approval_decision": decision_name,
                "approval_decision_id": decision_id,
                "status": "failed",
                "error_code": "approval_cannot_override_read_only",
                "error_message": "approval cannot override the read-only SQL boundary",
                "trajectory": [
                    _event(
                        state,
                        node="approval_gate",
                        status="failed",
                        details={
                            "decision": decision_name,
                            "decision_id": decision_id,
                            "error_code": "approval_cannot_override_read_only",
                        },
                    )
                ],
            }

        return {
            "approval_decision": decision_name,
            "approval_decision_id": decision_id,
            "status": "approval_granted",
            "error_code": None,
            "error_message": None,
            "trajectory": [
                _event(
                    state,
                    node="approval_gate",
                    status="approved",
                    details={
                        "decision": decision_name,
                        "decision_id": decision_id,
                    },
                )
            ],
        }

    def execute_sql(state: WorkflowState) -> dict[str, Any]:
        attempt_count = state.get("attempt_count", 0) + 1
        try:
            result = execute_read_only(business_database, state["generated_sql"])
            rows = [
                [_json_scalar(value) for value in row]
                for row in result.rows
            ]
        except ReadOnlyViolation:
            return _failure(
                state,
                node="execute_sql",
                code="read_only_violation",
                message="generated SQL violated the read-only contract",
                attempt_count=attempt_count,
            )
        except QueryTimeoutError:
            return _failure(
                state,
                node="execute_sql",
                code="query_timeout",
                message="generated SQL exceeded the execution deadline",
                attempt_count=attempt_count,
            )
        except QueryExecutionError:
            return _failure(
                state,
                node="execute_sql",
                code="query_execution_error",
                message="generated SQL could not be executed",
                attempt_count=attempt_count,
            )
        except UnsupportedResultType:
            return _failure(
                state,
                node="execute_sql",
                code="unsupported_result_type",
                message="query result cannot be represented as JSON",
                attempt_count=attempt_count,
            )
        return {
            "query_columns": list(result.columns),
            "query_rows": rows,
            "truncated": result.truncated,
            "attempt_count": attempt_count,
            "status": "executed",
            "trajectory": [
                _event(
                    state,
                    node="execute_sql",
                    status="completed",
                    details={
                        "returned_row_count": result.returned_row_count,
                        "truncated": result.truncated,
                    },
                )
            ],
        }

    def finish(state: WorkflowState) -> dict[str, Any]:
        return {
            "status": "completed",
            "error_code": None,
            "error_message": None,
            "trajectory": [
                _event(
                    state,
                    node="finish",
                    status="completed",
                    details={"result_available": True},
                )
            ],
        }

    def after_schema(state: WorkflowState) -> str:
        return "stop" if state["status"] == "failed" else "draft_sql"

    def after_draft(state: WorkflowState) -> str:
        return "stop" if state["status"] == "failed" else "assess_sql"

    def after_assessment(state: WorkflowState) -> str:
        if state["status"] == "pending_approval":
            return "approval_gate"
        return "execute_sql"

    def after_approval(state: WorkflowState) -> str:
        return "execute_sql" if state["status"] == "approval_granted" else "stop"

    def after_execute(state: WorkflowState) -> str:
        return "stop" if state["status"] == "failed" else "finish"

    builder = StateGraph(WorkflowState)
    builder.add_node("load_schema", load_schema)
    builder.add_node("draft_sql", draft_sql)
    builder.add_node("assess_sql", assess_sql)
    builder.add_node("approval_gate", approval_gate)
    builder.add_node("execute_sql", execute_sql)
    builder.add_node("finish", finish)
    builder.add_edge(START, "load_schema")
    builder.add_conditional_edges(
        "load_schema", after_schema, {"stop": END, "draft_sql": "draft_sql"}
    )
    builder.add_conditional_edges(
        "draft_sql", after_draft, {"stop": END, "assess_sql": "assess_sql"}
    )
    builder.add_conditional_edges(
        "assess_sql",
        after_assessment,
        {"approval_gate": "approval_gate", "execute_sql": "execute_sql"},
    )
    builder.add_conditional_edges(
        "approval_gate",
        after_approval,
        {"stop": END, "execute_sql": "execute_sql"},
    )
    builder.add_conditional_edges(
        "execute_sql", after_execute, {"stop": END, "finish": "finish"}
    )
    builder.add_edge("finish", END)
    return builder.compile(checkpointer=checkpointer)


class WorkflowRunner:
    """Own a synchronous graph/checkpointer pair and expose stable run records."""

    def __init__(
        self,
        business_database: str | Path,
        checkpoint_database: str | Path,
        *,
        generator: SqlGenerator | None = None,
        approval_row_limit: int = DEFAULT_APPROVAL_ROW_LIMIT,
    ) -> None:
        if type(approval_row_limit) is not int or approval_row_limit <= 0:
            raise ValueError("approval_row_limit must be a positive integer")
        self._business_database = Path(business_database).resolve()
        self._checkpoint_database = Path(checkpoint_database).resolve()
        if self._business_database == self._checkpoint_database:
            raise ValueError("business and checkpoint databases must be different files")
        self._checkpoint_database.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(
            self._checkpoint_database,
            check_same_thread=False,
        )
        serializer = JsonPlusSerializer(
            pickle_fallback=False,
            allowed_msgpack_modules=[],
        )
        try:
            self._graph = _build_graph(
                business_database=self._business_database,
                generator=generator or StaticSqlGenerator(),
                approval_row_limit=approval_row_limit,
                checkpointer=SqliteSaver(self._connection, serde=serializer),
            )
        except Exception:
            self._connection.close()
            raise
        self._closed = False

    def __enter__(self) -> WorkflowRunner:
        self._ensure_open()
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _traceback: Any) -> None:
        self.close()

    def close(self) -> None:
        if not self._closed:
            self._connection.close()
            self._closed = True

    def run(self, *, run_id: str, question: str) -> dict[str, Any]:
        self._ensure_open()
        normalized_run_id = self._validate_run_id(run_id)
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("question must not be empty")
        if len(normalized_question) > 2_000:
            raise ValueError("question exceeds the 2000 character limit")

        config = self._config(normalized_run_id)
        if self._graph.get_state(config).values:
            raise DuplicateRunError(f"run ID already exists: {normalized_run_id}")
        self._graph.invoke(
            {
                "run_id": normalized_run_id,
                "question": normalized_question,
                "status": "received",
                "error_code": None,
                "error_message": None,
                "attempt_count": 0,
                "trajectory": [],
            },
            config,
        )
        return self.get_run(normalized_run_id)

    def decide(
        self,
        *,
        run_id: str,
        decision_id: str,
        approved: bool,
    ) -> dict[str, Any]:
        self._ensure_open()
        normalized_run_id = self._validate_run_id(run_id)
        normalized_decision_id = self._validate_decision_id(decision_id)
        if type(approved) is not bool:
            raise InvalidApprovalDecisionError("approved must be a boolean")

        config = self._config(normalized_run_id)
        snapshot = self._graph.get_state(config)
        if not snapshot.values:
            raise RunNotFoundError(f"run ID was not found: {normalized_run_id}")
        if (
            snapshot.values.get("status") != "pending_approval"
            or tuple(snapshot.next) != ("approval_gate",)
        ):
            raise InvalidApprovalDecisionError(
                f"run is not awaiting approval: {normalized_run_id}"
            )

        self._graph.invoke(
            Command(
                resume={
                    "approved": approved,
                    "decision_id": normalized_decision_id,
                }
            ),
            config,
        )
        return self.get_run(normalized_run_id)

    def get_run(self, run_id: str) -> dict[str, Any]:
        self._ensure_open()
        normalized_run_id = self._validate_run_id(run_id)
        config = self._config(normalized_run_id)
        snapshot = self._graph.get_state(config)
        if not snapshot.values:
            raise RunNotFoundError(f"run ID was not found: {normalized_run_id}")
        checkpoint_count = sum(1 for _ in self._graph.get_state_history(config))
        return self._project(snapshot.values, checkpoint_count=checkpoint_count)

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("workflow runner is closed")

    @staticmethod
    def _validate_run_id(run_id: str) -> str:
        normalized = run_id.strip()
        if not _RUN_ID_PATTERN.fullmatch(normalized):
            raise ValueError(
                "run_id must be 1-64 characters using letters, digits, dot, underscore, or hyphen"
            )
        return normalized

    @staticmethod
    def _validate_decision_id(decision_id: str) -> str:
        if not isinstance(decision_id, str):
            raise InvalidApprovalDecisionError("decision_id must be a string")
        normalized = decision_id.strip()
        if not _DECISION_ID_PATTERN.fullmatch(normalized):
            raise InvalidApprovalDecisionError(
                "decision_id must be 1-64 characters using letters, digits, dot, "
                "underscore, or hyphen"
            )
        return normalized

    @staticmethod
    def _config(run_id: str) -> dict[str, dict[str, str]]:
        return {"configurable": {"thread_id": run_id}}

    @staticmethod
    def _project(state: Mapping[str, Any], *, checkpoint_count: int) -> dict[str, Any]:
        approval = None
        if state.get("approval_required"):
            approval = {
                "required": True,
                "reason": state.get("approval_reason"),
                "threshold": state.get("approval_threshold"),
                "requested_row_limit": state.get("approval_requested_row_limit"),
                "can_execute": state.get("approval_can_execute"),
                "decision": state.get("approval_decision"),
                "decision_id": state.get("approval_decision_id"),
            }
        record = {
            "schema_version": RUN_RECORD_SCHEMA_VERSION,
            "run_id": state["run_id"],
            "question": state["question"],
            "status": state["status"],
            "schema_snapshot": state.get("schema_snapshot", []),
            "generated_sql": state.get("generated_sql"),
            "query_columns": state.get("query_columns", []),
            "query_rows": state.get("query_rows", []),
            "truncated": state.get("truncated"),
            "attempt_count": state.get("attempt_count", 0),
            "error_code": state.get("error_code"),
            "error_message": state.get("error_message"),
            "approval": approval,
            "trajectory": state.get("trajectory", []),
            "checkpoint_count": checkpoint_count,
        }
        return json.loads(json.dumps(record, allow_nan=False, ensure_ascii=False))
