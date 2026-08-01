"""Deterministic answer projection from a fully bound evidence envelope."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .evidence import bind_evidence, verify_evidence


ANSWER_SCHEMA_VERSION = "answer-v1"


class AnswerCompositionError(ValueError):
    """Raised when evidence cannot safely support a deterministic answer."""

    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _validated_evidence(evidence: object) -> dict[str, Any]:
    if not verify_evidence(evidence):
        raise AnswerCompositionError(
            code="evidence_verification_failed",
            message="evidence fingerprint verification failed",
        )
    if not isinstance(evidence, Mapping):
        raise AnswerCompositionError(
            code="evidence_contract_invalid",
            message="evidence does not match the binding contract",
        )

    payload = evidence.get("payload")
    if not isinstance(payload, Mapping):
        raise AnswerCompositionError(
            code="evidence_contract_invalid",
            message="evidence does not match the binding contract",
        )
    result = payload.get("result")
    if not isinstance(result, Mapping):
        raise AnswerCompositionError(
            code="evidence_contract_invalid",
            message="evidence does not match the binding contract",
        )

    try:
        regenerated = bind_evidence(
            run_id=payload["run_id"],
            question=payload["question"],
            sql=payload["sql"],
            schema_snapshot=payload["schema_snapshot"],
            columns=result["columns"],
            rows=result["rows"],
            truncated=result["truncated"],
            validation=payload["validation"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AnswerCompositionError(
            code="evidence_contract_invalid",
            message="evidence does not match the binding contract",
        ) from exc
    if regenerated != dict(evidence):
        raise AnswerCompositionError(
            code="evidence_contract_invalid",
            message="evidence does not match the binding contract",
        )
    return regenerated


def _format_value(value: Any) -> str:
    return json.dumps(value, allow_nan=False, ensure_ascii=False)


def compose_answer(evidence: object) -> dict[str, Any]:
    """Create an answer that states only facts directly represented in evidence."""

    validated = _validated_evidence(evidence)
    payload = validated["payload"]
    result = payload["result"]
    columns = result["columns"]
    rows = result["rows"]

    if not rows:
        text = "查询未返回数据。"
        references = [
            {
                "kind": "result_metadata",
                "path": "payload.result.returned_row_count",
                "value": 0,
            }
        ]
    elif len(rows) == 1:
        text = "查询结果：" + "，".join(
            f"{column} = {_format_value(rows[0][index])}"
            for index, column in enumerate(columns)
        ) + "。"
        references = [
            {
                "kind": "result_cell",
                "path": f"payload.result.rows[0][{index}]",
                "row_index": 0,
                "column": column,
                "value": rows[0][index],
            }
            for index, column in enumerate(columns)
        ]
    else:
        text = f"查询返回 {len(rows)} 行，字段：{'、'.join(columns)}。"
        references = [
            {
                "kind": "result_metadata",
                "path": "payload.result.returned_row_count",
                "value": len(rows),
            },
            {
                "kind": "result_metadata",
                "path": "payload.result.columns",
                "value": columns,
            },
        ]

    return {
        "schema_version": ANSWER_SCHEMA_VERSION,
        "text": text,
        "source": {
            "evidence_schema_version": validated["schema_version"],
            "evidence_fingerprint": validated["fingerprint"]["value"],
            "references": references,
        },
    }
