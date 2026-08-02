from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from typing import Any

from auditable_nl2sql import (
    ProviderDecisionError,
    SqlGenerationResult,
    execute_read_only,
    read_schema,
)
from evals.contract import DatasetContractError, load_cases, validate_reference_cases
from evals.runner import run_model_evaluation
from evals.schema_holdout import (
    MAIN_COLUMN_NAMES,
    MAIN_TABLE_NAMES,
    SCHEMA_HOLDOUT_CASE_IDS,
    SCHEMA_HOLDOUT_CATEGORY_COUNTS,
    SCHEMA_HOLDOUT_TABLE_COLUMNS,
    SchemaHoldoutContractError,
    create_schema_holdout_database,
    validate_schema_holdout_contract,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_DATASET_PATH = PROJECT_ROOT / "evals/cases.jsonl"
HOLDOUT_DATASET_PATH = PROJECT_ROOT / "evals/schema_holdout_cases.jsonl"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FrozenHoldoutOutcomeGenerator:
    def __init__(self) -> None:
        self._cases = {
            case["question"]: case for case in load_cases(HOLDOUT_DATASET_PATH)
        }
        self.calls: list[str] = []

    def generate(
        self,
        question: str,
        schema_snapshot: list[dict[str, Any]],
    ) -> SqlGenerationResult:
        self.calls.append(question)
        self.assert_schema(schema_snapshot)
        case = self._cases[question]
        action = {
            "success": "query",
            "ambiguity": "clarify",
            "no_answer": "no_answer",
            "unauthorized": "unsafe_operation",
            "injection": "block",
        }[case["category"]]
        sql = case["reference_sql"]
        if action == "unsafe_operation" and sql is None:
            sql = "UPDATE transaction_lines SET paid_unit_cents = 0"
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
            "reason": "Deterministic schema HOLDOUT fixture",
        }
        if action in {"block", "clarify", "no_answer"}:
            raise ProviderDecisionError(action, receipt=receipt)
        return SqlGenerationResult(action=action, sql=sql, receipt=receipt)

    @staticmethod
    def assert_schema(schema_snapshot: list[dict[str, Any]]) -> None:
        actual = {table["name"] for table in schema_snapshot}
        if actual != set(SCHEMA_HOLDOUT_TABLE_COLUMNS):
            raise AssertionError(f"unexpected schema snapshot: {sorted(actual)}")


class SchemaHoldoutTests(unittest.TestCase):
    def test_fixture_has_different_deterministic_schema_and_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            first = create_schema_holdout_database(root / "first.sqlite3")
            second = create_schema_holdout_database(root / "second.sqlite3")

            self.assertEqual(_sha256(first), _sha256(second))
            schema = read_schema(first)
            actual_columns = {
                table.name: tuple(column.name for column in table.columns)
                for table in schema
            }
            self.assertEqual(actual_columns, SCHEMA_HOLDOUT_TABLE_COLUMNS)
            self.assertTrue(set(actual_columns).isdisjoint(MAIN_TABLE_NAMES))
            all_columns = {
                column for columns in actual_columns.values() for column in columns
            }
            self.assertTrue(all_columns.isdisjoint(MAIN_COLUMN_NAMES))
            declared_types = {
                column.name: column.declared_type
                for table in schema
                for column in table.columns
            }
            self.assertEqual(declared_types["catalog_price_cents"], "INTEGER")
            self.assertEqual(declared_types["paid_unit_cents"], "INTEGER")
            self.assertEqual(
                execute_read_only(
                    first,
                    "SELECT (SELECT COUNT(*) FROM buyer_directory), "
                    "(SELECT COUNT(*) FROM merchandise), "
                    "(SELECT COUNT(*) FROM transaction_lines), "
                    "(SELECT COUNT(DISTINCT ticket_no) FROM transaction_lines)",
                ).rows,
                ((4, 5, 11, 6),),
            )
            self.assertEqual(
                execute_read_only(
                    first,
                    "SELECT DISTINCT state_code FROM transaction_lines "
                    "ORDER BY state_code",
                ).rows,
                (("CLOSED",), ("IN_TRANSIT",), ("SETTLED",), ("VOID",)),
            )
            self.assertEqual(
                execute_read_only(
                    first,
                    "SELECT DISTINCT source_code FROM transaction_lines "
                    "ORDER BY source_code",
                ).rows,
                (("PLATFORM",), ("SHOP",), ("WEB",)),
            )

    def test_fixture_refuses_to_overwrite_existing_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = create_schema_holdout_database(
                Path(temporary_directory) / "business.sqlite3"
            )
            before = _sha256(path)

            with self.assertRaises(FileExistsError):
                create_schema_holdout_database(path)

            self.assertEqual(_sha256(path), before)

    def test_holdout_contract_maps_exact_source_cases_and_rejects_drift(self) -> None:
        main_cases = {case["case_id"]: case for case in load_cases(MAIN_DATASET_PATH)}
        holdout_cases = load_cases(HOLDOUT_DATASET_PATH)

        validate_schema_holdout_contract(holdout_cases)
        self.assertEqual(
            [case["case_id"] for case in holdout_cases],
            list(SCHEMA_HOLDOUT_CASE_IDS),
        )
        self.assertEqual(
            Counter(case["category"] for case in holdout_cases),
            Counter(SCHEMA_HOLDOUT_CATEGORY_COUNTS),
        )
        for case in holdout_cases:
            source = main_cases[case["case_id"]]
            self.assertEqual(case["question"], source["question"])
            self.assertEqual(case["expected"], source["expected"])
            if case["reference_sql"] is not None:
                self.assertNotEqual(case["reference_sql"], source["reference_sql"])

        invalid_payloads = []
        unknown_field = copy.deepcopy(holdout_cases)
        unknown_field[0]["unexpected"] = True
        invalid_payloads.append(unknown_field)
        changed_question = copy.deepcopy(holdout_cases)
        changed_question[0]["question"] += " "
        invalid_payloads.append(changed_question)
        copied_main_sql = copy.deepcopy(holdout_cases)
        copied_main_sql[0]["reference_sql"] = main_cases["success-001"][
            "reference_sql"
        ]
        invalid_payloads.append(copied_main_sql)

        for invalid in invalid_payloads:
            with self.subTest(invalid=invalid[0]):
                with self.assertRaises(SchemaHoldoutContractError):
                    validate_schema_holdout_contract(invalid)

    def test_holdout_references_reproduce_results_without_mutation(self) -> None:
        cases = load_cases(HOLDOUT_DATASET_PATH)
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            business = create_schema_holdout_database(root / "business.sqlite3")
            before = _sha256(business)

            validate_reference_cases(
                cases,
                business_database=business,
                checkpoint_database=root / "workflow.sqlite3",
                case_validator=validate_schema_holdout_contract,
            )

            self.assertEqual(_sha256(business), before)

    def test_runner_requires_explicit_holdout_contract_and_preserves_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            business = create_schema_holdout_database(root / "business.sqlite3")
            generator = FrozenHoldoutOutcomeGenerator()

            with self.assertRaises(DatasetContractError):
                run_model_evaluation(
                    HOLDOUT_DATASET_PATH,
                    business_database=business,
                    checkpoint_database=root / "wrong-contract.sqlite3",
                    generator=generator,
                    evaluation_id="wrong-contract",
                )
            self.assertEqual(generator.calls, [])
            report = run_model_evaluation(
                HOLDOUT_DATASET_PATH,
                business_database=business,
                checkpoint_database=root / "workflow.sqlite3",
                generator=generator,
                evaluation_id="schema-holdout-test",
                case_validator=validate_schema_holdout_contract,
            )

            self.assertEqual(
                generator.calls,
                [case["question"] for case in load_cases(HOLDOUT_DATASET_PATH)],
            )
            self.assertEqual(
                report["metrics"]["execution_success_rate"],
                {"numerator": 7, "denominator": 7, "value": 1.0},
            )
            self.assertEqual(
                report["metrics"]["answer_correctness"],
                {"numerator": 15, "denominator": 15, "value": 1.0},
            )
            self.assertEqual(
                report["metrics"]["human_intervention_rate"],
                {"numerator": 2, "denominator": 15, "value": 2 / 15},
            )
            self.assertEqual(
                report["provider_usage"],
                {
                    "reported_case_count": 15,
                    "prompt_tokens": 150,
                    "completion_tokens": 30,
                    "total_tokens": 180,
                },
            )
            self.assertEqual(report["safety"]["non_success_execution_attempts"], 0)
            self.assertEqual(report["safety"]["unauthorized_execution_attempts"], 0)
            self.assertTrue(report["safety"]["business_database_unchanged"])


if __name__ == "__main__":
    unittest.main()
