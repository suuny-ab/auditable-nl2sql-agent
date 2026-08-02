from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from auditable_nl2sql import ProviderDecisionError, SqlGenerationResult
from auditable_nl2sql.demo import create_demo_database
from evals.contract import load_cases
from evals.runner import (
    EvaluationRunnerError,
    run_model_evaluation,
    write_evaluation_report,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "evals" / "cases.jsonl"


class FrozenOutcomeGenerator:
    def __init__(self, *, injected_failure: bool = False) -> None:
        self._cases = {
            case["question"]: case for case in load_cases(DATASET_PATH)
        }
        self._injected_failure = injected_failure
        self.calls: list[str] = []

    def generate(
        self,
        question: str,
        schema_snapshot: list[dict[str, Any]],
    ) -> SqlGenerationResult:
        self.calls.append(question)
        if not schema_snapshot:
            raise AssertionError("schema snapshot must be supplied")
        case = self._cases[question]
        category = case["category"]
        action = {
            "success": "query",
            "ambiguity": "clarify",
            "no_answer": "no_answer",
            "unauthorized": "unsafe_operation",
            "injection": "block",
        }[category]
        sql = case["reference_sql"]
        if action == "unsafe_operation" and sql is None:
            sql = "DELETE FROM orders"
        if self._injected_failure and case["case_id"] == "injection-001":
            action = "query"
            sql = "SELECT 1 AS injected"
        receipt = {
            "schema_version": "provider-receipt-v1",
            "provider": "deepseek",
            "requested_model": "fake-model",
            "response_model": "fake-model",
            "finish_reason": "stop",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 2,
                "total_tokens": 12,
            },
            "action": action,
            "reason": "Deterministic evaluation fixture",
        }
        if action in {"block", "clarify", "no_answer"}:
            raise ProviderDecisionError(action, receipt=receipt)
        return SqlGenerationResult(action=action, sql=sql, receipt=receipt)


class ModelEvaluationRunnerTests(unittest.TestCase):
    def test_ideal_forty_case_run_produces_exact_metrics_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            business = create_demo_database(root / "business.sqlite3")
            generator = FrozenOutcomeGenerator()

            report = run_model_evaluation(
                DATASET_PATH,
                business_database=business,
                checkpoint_database=root / "workflow.sqlite3",
                generator=generator,
                evaluation_id="ideal",
            )

            self.assertEqual(len(generator.calls), 40)
            self.assertEqual(len(set(generator.calls)), 40)
            self.assertEqual(report["schema_version"], "model-evaluation-report-v1")
            self.assertEqual(len(report["cases"]), 40)
            self.assertEqual(
                report["metrics"]["execution_success_rate"],
                {"numerator": 16, "denominator": 16, "value": 1.0},
            )
            self.assertEqual(
                report["metrics"]["answer_correctness"],
                {"numerator": 40, "denominator": 40, "value": 1.0},
            )
            self.assertEqual(
                report["metrics"]["human_intervention_rate"],
                {"numerator": 6, "denominator": 40, "value": 0.15},
            )
            self.assertEqual(
                report["provider_usage"],
                {
                    "reported_case_count": 40,
                    "prompt_tokens": 400,
                    "completion_tokens": 80,
                    "total_tokens": 480,
                },
            )
            self.assertTrue(report["safety"]["business_database_unchanged"])
            self.assertEqual(report["safety"]["non_success_execution_attempts"], 0)
            self.assertEqual(report["safety"]["unauthorized_execution_attempts"], 0)
            self.assertEqual(
                report["business_database_sha256_before"],
                report["business_database_sha256_after"],
            )
            self.assertTrue(
                all(case["run_record"]["trajectory"] for case in report["cases"])
            )
            self.assertTrue(
                all(
                    case["database_sha256_after_case"]
                    == report["business_database_sha256_before"]
                    for case in report["cases"]
                )
            )

            output = write_evaluation_report(report, root / "report.json")
            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8")),
                report,
            )
            with self.assertRaises(FileExistsError):
                write_evaluation_report(report, output)
            invalid_output = root / "invalid-report.json"
            with self.assertRaises(EvaluationRunnerError):
                write_evaluation_report({"metric": float("nan")}, invalid_output)
            self.assertFalse(invalid_output.exists())

    def test_wrong_injection_action_is_counted_as_an_incorrect_answer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            business = create_demo_database(root / "business.sqlite3")
            generator = FrozenOutcomeGenerator(injected_failure=True)

            report = run_model_evaluation(
                DATASET_PATH,
                business_database=business,
                checkpoint_database=root / "workflow.sqlite3",
                generator=generator,
                evaluation_id="wrong-injection",
            )

            self.assertEqual(
                report["metrics"]["execution_success_rate"]["numerator"],
                16,
            )
            self.assertEqual(
                report["metrics"]["answer_correctness"],
                {"numerator": 39, "denominator": 40, "value": 39 / 40},
            )
            failed = next(
                case for case in report["cases"] if case["case_id"] == "injection-001"
            )
            self.assertFalse(failed["adjudication"]["answer_correct"])
            self.assertIn(
                "provider_action_mismatch",
                failed["adjudication"]["reasons"],
            )
            self.assertIn(
                "unexpected_sql_execution",
                failed["adjudication"]["reasons"],
            )
            self.assertEqual(failed["run_record"]["attempt_count"], 1)
            self.assertEqual(report["safety"]["non_success_execution_attempts"], 1)
            self.assertTrue(report["safety"]["business_database_unchanged"])


if __name__ == "__main__":
    unittest.main()
