"""Strict result validation and deterministic evidence binding."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
from collections.abc import Mapping
from typing import Any


EVIDENCE_SCHEMA_VERSION = "evidence-v1"
EVIDENCE_CANONICALIZATION = "canonical-json-v1"


class ResultValidationError(ValueError):
    """Raised when an executed query result cannot support bound evidence."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        checks: list[dict[str, Any]],
    ) -> None:
        super().__init__(message)
        self.code = code
        self.checks = checks


class EvidenceBindingError(ValueError):
    """Raised when evidence cannot be represented by the versioned contract."""


def _is_json_scalar(value: Any) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    return value is None or isinstance(value, (str, int, bool))


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": passed}


def validate_result(
    *,
    columns: list[str],
    rows: list[list[Any]],
    truncated: bool,
) -> dict[str, Any]:
    """Return a stable validation receipt or fail closed with a specific code."""

    columns_valid = (
        isinstance(columns, list)
        and bool(columns)
        and all(isinstance(column, str) and bool(column) for column in columns)
    )
    rows_are_lists = isinstance(rows, list) and all(
        isinstance(row, list) for row in rows
    )
    row_width_valid = rows_are_lists and columns_valid and all(
        len(row) == len(columns) for row in rows
    )
    not_truncated = truncated is False
    scalar_types_valid = rows_are_lists and all(
        _is_json_scalar(value) for row in rows for value in row
    )
    checks = [
        _check("columns_present", columns_valid),
        _check("rows_are_lists", rows_are_lists),
        _check("row_width_matches_columns", row_width_valid),
        _check("not_truncated", not_truncated),
        _check("json_scalars_only", scalar_types_valid),
    ]

    if not columns_valid:
        raise ResultValidationError(
            code="result_columns_invalid",
            message="query result columns are invalid",
            checks=checks,
        )
    if not rows_are_lists or not row_width_valid:
        raise ResultValidationError(
            code="result_row_shape_invalid",
            message="query result row shape does not match its columns",
            checks=checks,
        )
    if not not_truncated:
        raise ResultValidationError(
            code="result_truncated",
            message="truncated query results cannot produce evidence",
            checks=checks,
        )
    if not scalar_types_valid:
        raise ResultValidationError(
            code="result_type_invalid",
            message="query result contains a value outside the strict JSON contract",
            checks=checks,
        )

    return {
        "status": "passed",
        "checks": checks,
        "returned_row_count": len(rows),
    }


def _canonical_payload_bytes(payload: Mapping[str, Any]) -> bytes:
    try:
        encoded = json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise EvidenceBindingError("evidence payload is not strict JSON") from exc
    return encoded.encode("utf-8")


def bind_evidence(
    *,
    run_id: str,
    question: str,
    sql: str,
    schema_snapshot: list[dict[str, Any]],
    columns: list[str],
    rows: list[list[Any]],
    truncated: bool,
    validation: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind validated run inputs into a self-contained evidence envelope."""

    for name, value in (("run_id", run_id), ("question", question), ("sql", sql)):
        if not isinstance(value, str) or not value:
            raise EvidenceBindingError(f"{name} must be a non-empty string")
    if not isinstance(schema_snapshot, list) or not schema_snapshot:
        raise EvidenceBindingError("schema_snapshot must contain at least one table")

    expected_validation = validate_result(
        columns=columns,
        rows=rows,
        truncated=truncated,
    )
    if dict(validation) != expected_validation:
        raise EvidenceBindingError("validation receipt does not match the query result")

    payload = {
        "run_id": run_id,
        "question": question,
        "sql": sql,
        "schema_snapshot": schema_snapshot,
        "result": {
            "columns": columns,
            "rows": rows,
            "returned_row_count": len(rows),
            "truncated": truncated,
        },
        "validation": expected_validation,
    }
    canonical = _canonical_payload_bytes(payload)
    normalized_payload = json.loads(canonical.decode("utf-8"))
    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "payload": normalized_payload,
        "fingerprint": {
            "algorithm": "sha256",
            "canonicalization": EVIDENCE_CANONICALIZATION,
            "value": hashlib.sha256(canonical).hexdigest(),
        },
    }


def verify_evidence(evidence: object) -> bool:
    """Return whether an evidence envelope matches its canonical payload hash."""

    if not isinstance(evidence, Mapping):
        return False
    if set(evidence) != {"schema_version", "payload", "fingerprint"}:
        return False
    if evidence.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        return False
    payload = evidence.get("payload")
    fingerprint = evidence.get("fingerprint")
    if not isinstance(payload, Mapping) or not isinstance(fingerprint, Mapping):
        return False
    if set(fingerprint) != {"algorithm", "canonicalization", "value"}:
        return False
    if fingerprint.get("algorithm") != "sha256":
        return False
    if fingerprint.get("canonicalization") != EVIDENCE_CANONICALIZATION:
        return False
    expected = fingerprint.get("value")
    if not isinstance(expected, str) or len(expected) != 64:
        return False
    try:
        actual = hashlib.sha256(_canonical_payload_bytes(payload)).hexdigest()
    except EvidenceBindingError:
        return False
    return hmac.compare_digest(actual, expected)
