from __future__ import annotations

import copy
import hashlib
import json
import unittest
from typing import Any

from auditable_nl2sql import (
    AnswerCompositionError,
    bind_evidence,
    compose_answer,
    validate_result,
    verify_evidence,
)


def _evidence(*, columns: list[str], rows: list[list[Any]]) -> dict[str, Any]:
    validation = validate_result(columns=columns, rows=rows, truncated=False)
    return bind_evidence(
        run_id="answer-001",
        question="测试问题",
        sql="SELECT synthetic_result",
        schema_snapshot=[
            {
                "name": "synthetic_table",
                "columns": [
                    {
                        "name": column,
                        "declared_type": "TEXT",
                        "nullable": True,
                        "primary_key_position": 0,
                        "default_value": None,
                    }
                    for column in columns
                ],
                "foreign_keys": [],
            }
        ],
        columns=columns,
        rows=rows,
        truncated=False,
        validation=validation,
    )


class AnswerCompositionTests(unittest.TestCase):
    def test_single_row_answer_references_exact_result_cells(self) -> None:
        evidence = _evidence(columns=["revenue"], rows=[[5946.0]])

        answer = compose_answer(evidence)

        self.assertEqual(answer["schema_version"], "answer-v1")
        self.assertEqual(answer["text"], "查询结果：revenue = 5946.0。")
        self.assertEqual(
            answer["source"]["evidence_fingerprint"],
            evidence["fingerprint"]["value"],
        )
        self.assertEqual(
            answer["source"]["references"],
            [
                {
                    "kind": "result_cell",
                    "path": "payload.result.rows[0][0]",
                    "row_index": 0,
                    "column": "revenue",
                    "value": 5946.0,
                }
            ],
        )

    def test_zero_and_multi_row_answers_make_only_conservative_claims(self) -> None:
        empty = compose_answer(_evidence(columns=["order_id"], rows=[]))
        multiple = compose_answer(
            _evidence(
                columns=["order_id", "product_id"],
                rows=[["O1001", "P1001"], ["O1001", "P1002"]],
            )
        )

        self.assertEqual(empty["text"], "查询未返回数据。")
        self.assertEqual(
            empty["source"]["references"][0]["path"],
            "payload.result.returned_row_count",
        )
        self.assertEqual(
            multiple["text"],
            "查询返回 2 行，字段：order_id、product_id。",
        )
        self.assertEqual(
            [reference["path"] for reference in multiple["source"]["references"]],
            ["payload.result.returned_row_count", "payload.result.columns"],
        )

    def test_tampered_or_contract_invalid_evidence_fails_closed(self) -> None:
        evidence = _evidence(columns=["revenue"], rows=[[5946.0]])
        tampered = copy.deepcopy(evidence)
        tampered["payload"]["result"]["rows"] = [[9999.0]]

        with self.assertRaises(AnswerCompositionError) as fingerprint_error:
            compose_answer(tampered)
        self.assertEqual(
            fingerprint_error.exception.code,
            "evidence_verification_failed",
        )

        malformed = copy.deepcopy(evidence)
        malformed["payload"]["unexpected"] = True
        canonical = json.dumps(
            malformed["payload"],
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        malformed["fingerprint"]["value"] = hashlib.sha256(canonical).hexdigest()
        self.assertTrue(verify_evidence(malformed))

        with self.assertRaises(AnswerCompositionError) as contract_error:
            compose_answer(malformed)
        self.assertEqual(contract_error.exception.code, "evidence_contract_invalid")


if __name__ == "__main__":
    unittest.main()
