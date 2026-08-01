from __future__ import annotations

import copy
import unittest
from typing import Any

from auditable_nl2sql import (
    EvidenceBindingError,
    ResultValidationError,
    bind_evidence,
    validate_result,
    verify_evidence,
)


class ResultValidationTests(unittest.TestCase):
    def test_valid_result_returns_stable_receipt(self) -> None:
        receipt = validate_result(
            columns=["order_id", "amount"],
            rows=[["O1001", 120.5], ["O1002", None]],
            truncated=False,
        )

        self.assertEqual(receipt["status"], "passed")
        self.assertEqual(receipt["returned_row_count"], 2)
        self.assertTrue(all(check["passed"] for check in receipt["checks"]))

    def test_invalid_results_fail_closed_with_specific_codes(self) -> None:
        cases = [
            ({"columns": [], "rows": [], "truncated": False}, "result_columns_invalid"),
            (
                {"columns": ["a", "b"], "rows": [[1]], "truncated": False},
                "result_row_shape_invalid",
            ),
            ({"columns": ["a"], "rows": [[1]], "truncated": True}, "result_truncated"),
            (
                {"columns": ["a"], "rows": [[float("nan")]], "truncated": False},
                "result_type_invalid",
            ),
            (
                {"columns": ["a"], "rows": [[b"bytes"]], "truncated": False},
                "result_type_invalid",
            ),
        ]

        for arguments, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                with self.assertRaises(ResultValidationError) as raised:
                    validate_result(**arguments)
                self.assertEqual(raised.exception.code, expected_code)


class EvidenceBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = [
            {
                "name": "orders",
                "columns": [{"name": "order_id", "declared_type": "TEXT"}],
                "foreign_keys": [],
            }
        ]
        self.columns = ["order_id"]
        self.rows = [["O1001"]]
        self.validation = validate_result(
            columns=self.columns,
            rows=self.rows,
            truncated=False,
        )

    def _bind(self, **overrides: object) -> dict[str, Any]:
        arguments: dict[str, Any] = {
            "run_id": "evidence-001",
            "question": "第一条订单是什么？",
            "sql": "SELECT order_id FROM orders LIMIT 1",
            "schema_snapshot": self.schema,
            "columns": self.columns,
            "rows": self.rows,
            "truncated": False,
            "validation": self.validation,
        }
        arguments.update(overrides)
        return bind_evidence(**arguments)

    def test_binding_is_order_independent_and_detects_payload_changes(self) -> None:
        evidence = self._bind()
        reordered_schema = [
            {
                "foreign_keys": [],
                "columns": [{"declared_type": "TEXT", "name": "order_id"}],
                "name": "orders",
            }
        ]
        reordered = self._bind(schema_snapshot=reordered_schema)

        self.assertEqual(evidence, reordered)
        self.assertTrue(verify_evidence(evidence))

        changed = copy.deepcopy(evidence)
        changed["payload"]["result"]["rows"] = [["O9999"]]
        self.assertFalse(verify_evidence(changed))

    def test_binding_rejects_a_mismatched_validation_receipt(self) -> None:
        mismatched = copy.deepcopy(self.validation)
        mismatched["returned_row_count"] = 9

        with self.assertRaises(EvidenceBindingError):
            self._bind(validation=mismatched)

        self.assertFalse(verify_evidence(None))


if __name__ == "__main__":
    unittest.main()
