"""Strict contract checks for the frozen synthetic evaluation dataset."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from auditable_nl2sql import (
    ResultValidationError,
    StaticSqlGenerator,
    WorkflowRunner,
    validate_result,
)


CASE_SCHEMA_VERSION = "eval-case-v1"
CATEGORY_COUNTS = {
    "success": 8,
    "ambiguity": 3,
    "no_answer": 3,
    "unauthorized": 3,
    "injection": 3,
}
EXPECTED_CASE_IDS = frozenset(
    f"{category}-{index:03d}"
    for category, count in CATEGORY_COUNTS.items()
    for index in range(1, count + 1)
)

_CASE_KEYS = {
    "schema_version",
    "case_id",
    "category",
    "question",
    "reference_sql",
    "expected",
}
_EXPECTED_KEYS = {
    "final_status",
    "error_code",
    "approval_required",
    "approval_can_execute",
    "result",
}
_RESULT_KEYS = {"columns", "rows", "truncated"}
_CATEGORY_OUTCOMES = {
    "success": ("completed", None),
    "ambiguity": ("clarification_required", "ambiguous_question"),
    "no_answer": ("no_answer", "insufficient_data"),
    "unauthorized": ("failed", "approval_cannot_override_read_only"),
    "injection": ("blocked", "prompt_injection"),
}


class DatasetContractError(ValueError):
    """Raised when the frozen evaluation dataset violates its versioned contract."""


def _reject_json_constant(value: str) -> None:
    raise DatasetContractError(f"non-standard JSON constant is not allowed: {value}")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DatasetContractError(message)


def load_cases(dataset_path: str | Path) -> list[dict[str, Any]]:
    """Load strict JSONL without accepting NaN or other non-standard constants."""

    path = Path(dataset_path)
    cases: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        _require(bool(raw_line.strip()), f"line {line_number}: blank lines are not allowed")
        try:
            value = json.loads(raw_line, parse_constant=_reject_json_constant)
        except (json.JSONDecodeError, DatasetContractError) as exc:
            raise DatasetContractError(f"line {line_number}: invalid JSON") from exc
        _require(isinstance(value, dict), f"line {line_number}: case must be an object")
        cases.append(value)
    return cases


def _validate_expected(case: Mapping[str, Any]) -> None:
    case_id = case["case_id"]
    category = case["category"]
    expected = case["expected"]
    _require(isinstance(expected, dict), f"{case_id}: expected must be an object")
    _require(set(expected) == _EXPECTED_KEYS, f"{case_id}: expected fields changed")

    final_status, error_code = _CATEGORY_OUTCOMES[category]
    _require(
        expected["final_status"] == final_status,
        f"{case_id}: final_status does not match category",
    )
    _require(
        expected["error_code"] == error_code,
        f"{case_id}: error_code does not match category",
    )
    _require(
        type(expected["approval_required"]) is bool,
        f"{case_id}: approval_required must be a boolean",
    )

    approval_required = expected["approval_required"]
    approval_can_execute = expected["approval_can_execute"]
    if category == "unauthorized":
        _require(approval_required, f"{case_id}: unauthorized SQL must require approval")
        _require(
            approval_can_execute is False,
            f"{case_id}: unauthorized SQL cannot be approved for execution",
        )
    elif category == "success" and approval_required:
        _require(
            approval_can_execute is True,
            f"{case_id}: approved success SQL must remain executable",
        )
    else:
        _require(
            approval_can_execute is None,
            f"{case_id}: approval_can_execute must be null without approval",
        )

    result = expected["result"]
    if category != "success":
        _require(result is None, f"{case_id}: non-success case cannot contain a result")
        return

    _require(isinstance(result, dict), f"{case_id}: success result must be an object")
    _require(set(result) == _RESULT_KEYS, f"{case_id}: result fields changed")
    try:
        validate_result(
            columns=result["columns"],
            rows=result["rows"],
            truncated=result["truncated"],
        )
    except (KeyError, ResultValidationError) as exc:
        raise DatasetContractError(f"{case_id}: invalid expected result") from exc


def validate_case_contract(cases: Iterable[Mapping[str, Any]]) -> None:
    """Validate count, schema, category, and per-case expectation invariants."""

    materialized = list(cases)
    _require(len(materialized) == 20, "dataset must contain exactly 20 cases")

    case_ids: list[str] = []
    questions: list[str] = []
    categories: list[str] = []
    for index, case in enumerate(materialized, start=1):
        _require(isinstance(case, Mapping), f"case {index}: must be an object")
        _require(set(case) == _CASE_KEYS, f"case {index}: fields changed")
        _require(
            case["schema_version"] == CASE_SCHEMA_VERSION,
            f"case {index}: unsupported schema version",
        )

        case_id = case["case_id"]
        category = case["category"]
        question = case["question"]
        _require(category in CATEGORY_COUNTS, f"{case_id}: unknown category")
        _require(
            isinstance(case_id, str)
            and re.fullmatch(rf"{re.escape(category)}-\d{{3}}", case_id) is not None,
            f"case {index}: case_id does not match category",
        )
        _require(
            isinstance(question, str) and question == question.strip() and bool(question),
            f"{case_id}: question must be a non-empty trimmed string",
        )

        reference_sql = case["reference_sql"]
        if category in {"success", "unauthorized"}:
            _require(
                isinstance(reference_sql, str)
                and reference_sql == reference_sql.strip()
                and bool(reference_sql),
                f"{case_id}: category requires reference SQL",
            )
        else:
            _require(
                reference_sql is None,
                f"{case_id}: category must not contain reference SQL",
            )

        _validate_expected(case)
        case_ids.append(case_id)
        questions.append(question)
        categories.append(category)

    _require(len(set(case_ids)) == len(case_ids), "case IDs must be unique")
    _require(set(case_ids) == EXPECTED_CASE_IDS, "frozen case IDs changed")
    _require(len(set(questions)) == len(questions), "questions must be unique")
    _require(
        Counter(categories) == Counter(CATEGORY_COUNTS),
        "category counts must remain 8/3/3/3/3",
    )


def validate_reference_cases(
    cases: Iterable[Mapping[str, Any]],
    *,
    business_database: str | Path,
    checkpoint_database: str | Path,
) -> None:
    """Re-run frozen SQL through the product workflow without computing metrics."""

    materialized = list(cases)
    validate_case_contract(materialized)
    executable = [
        case
        for case in materialized
        if case["category"] in {"success", "unauthorized"}
    ]
    generator = StaticSqlGenerator(
        {case["question"]: case["reference_sql"] for case in executable}
    )

    with WorkflowRunner(
        business_database,
        checkpoint_database,
        generator=generator,
    ) as runner:
        for case in executable:
            case_id = case["case_id"]
            expected = case["expected"]
            record = runner.run(
                run_id=f"eval-{case_id}",
                question=case["question"],
            )

            if expected["approval_required"]:
                _require(
                    record["status"] == "pending_approval",
                    f"{case_id}: expected pending approval",
                )
                _require(
                    record["approval"]["can_execute"]
                    is expected["approval_can_execute"],
                    f"{case_id}: approval executability changed",
                )
                record = runner.decide(
                    run_id=f"eval-{case_id}",
                    decision_id=f"approve-{case_id}",
                    approved=True,
                )
            else:
                _require(record["approval"] is None, f"{case_id}: unexpected approval")

            _require(
                record["status"] == expected["final_status"],
                f"{case_id}: final status changed",
            )
            _require(
                record["error_code"] == expected["error_code"],
                f"{case_id}: error code changed",
            )

            if case["category"] == "success":
                result = expected["result"]
                _require(
                    record["query_columns"] == result["columns"],
                    f"{case_id}: result columns changed",
                )
                _require(
                    record["query_rows"] == result["rows"],
                    f"{case_id}: result rows changed",
                )
                _require(
                    record["truncated"] is result["truncated"],
                    f"{case_id}: truncation state changed",
                )
            else:
                _require(record["attempt_count"] == 0, f"{case_id}: SQL was executed")
                _require(record["evidence"] is None, f"{case_id}: evidence was created")
                _require(record["answer"] is None, f"{case_id}: answer was created")
