from __future__ import annotations

import copy
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from auditable_nl2sql import DeepSeekSqlGenerator
from auditable_nl2sql.demo import create_demo_database
from evals.contract import DatasetContractError, validate_reference_cases
from evals.paraphrase import (
    REVENUE_RERUN_CASE_IDS,
    REWRITE_STYLES,
    SOURCE_BASELINE_CORRECTNESS,
    load_paraphrase_cases,
    load_revenue_paraphrase_rerun_cases,
    summarize_paraphrase_report,
    summarize_revenue_paraphrase_rerun,
    validate_paraphrase_case_contract,
    validate_revenue_paraphrase_rerun_contract,
)
from evals.runner import run_model_evaluation


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "evals" / "paraphrase_cases.json"


class NoNetworkTransport:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def complete(self, request_payload: object) -> object:
        self.calls.append(request_payload)
        raise AssertionError("targeted local-intent rerun must not call transport")


class ParaphraseEvaluationContractTests(unittest.TestCase):
    def test_dataset_has_ten_sources_three_distinct_styles_and_explicit_mapping(self) -> None:
        cases = load_paraphrase_cases(DATASET_PATH)

        validate_paraphrase_case_contract(cases)

        self.assertEqual(len(cases), 30)
        self.assertEqual(len({case["case_id"] for case in cases}), 30)
        self.assertEqual(len({case["question"] for case in cases}), 30)
        self.assertTrue(all(case["meaning_preserved"] is True for case in cases))
        self.assertEqual(
            Counter(case["source_case_id"] for case in cases),
            Counter({source_case_id: 3 for source_case_id in SOURCE_BASELINE_CORRECTNESS}),
        )
        for source_case_id in SOURCE_BASELINE_CORRECTNESS:
            source_cases = [case for case in cases if case["source_case_id"] == source_case_id]
            self.assertEqual({case["rewrite_style"] for case in source_cases}, REWRITE_STYLES)

    def test_reference_sql_replays_through_read_only_workflow(self) -> None:
        cases = load_paraphrase_cases(DATASET_PATH)
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            business = create_demo_database(root / "business.sqlite3")
            validate_reference_cases(
                cases,
                business_database=business,
                checkpoint_database=root / "workflow.sqlite3",
                case_validator=validate_paraphrase_case_contract,
            )

    def test_contract_rejects_missing_meaning_declaration_and_source_drift(self) -> None:
        cases = load_paraphrase_cases(DATASET_PATH)
        missing_declaration = copy.deepcopy(cases)
        missing_declaration[0]["meaning_preserved"] = False
        with self.assertRaises(DatasetContractError):
            validate_paraphrase_case_contract(missing_declaration)

        source_drift = copy.deepcopy(cases)
        source_drift[0]["expected"]["result"]["rows"] = [[0.0]]
        with self.assertRaises(DatasetContractError):
            validate_paraphrase_case_contract(source_drift)

    def test_comparison_reports_stability_drops_and_improvements(self) -> None:
        cases = load_paraphrase_cases(DATASET_PATH)
        report_cases = []
        for case in cases:
            answer_correct = SOURCE_BASELINE_CORRECTNESS[case["source_case_id"]]
            if case["case_id"] == "success-001-p1":
                answer_correct = False
            if case["case_id"] == "success-013-p1":
                answer_correct = True
            report_cases.append(
                {
                    "case_id": case["case_id"],
                    "adjudication": {"answer_correct": answer_correct},
                }
            )

        comparison = summarize_paraphrase_report(
            {"evaluation_id": "paraphrase-test", "cases": report_cases}
        )

        self.assertEqual(
            comparison["stability"]["matching_source_outcome"],
            {"numerator": 28, "denominator": 30},
        )
        self.assertEqual(
            comparison["stability"]["fully_stable_sources"],
            {"numerator": 8, "denominator": 10},
        )
        self.assertEqual(comparison["dropped_variants"], ["success-001-p1"])
        self.assertEqual(comparison["improved_variants"], ["success-013-p1"])

    def test_revenue_rerun_contract_selects_only_the_three_frozen_drops(self) -> None:
        cases = load_revenue_paraphrase_rerun_cases(DATASET_PATH)

        validate_revenue_paraphrase_rerun_contract(cases)

        self.assertEqual({case["case_id"] for case in cases}, REVENUE_RERUN_CASE_IDS)
        self.assertTrue(all(case["source_case_id"] == "ambiguity-001" for case in cases))
        changed = copy.deepcopy(cases)
        changed[0]["case_id"] = "ambiguity-006-p1"
        with self.assertRaises(DatasetContractError):
            validate_revenue_paraphrase_rerun_contract(changed)

    def test_revenue_rerun_comparison_projects_only_selected_improvements(self) -> None:
        report = {
            "evaluation_id": "revenue-rerun-test",
            "cases": [
                {
                    "case_id": case_id,
                    "adjudication": {"answer_correct": True},
                }
                for case_id in sorted(REVENUE_RERUN_CASE_IDS)
            ],
        }

        comparison = summarize_revenue_paraphrase_rerun(report)

        self.assertEqual(
            comparison["baseline"]["full_answer_correctness"],
            {"numerator": 24, "denominator": 30},
        )
        self.assertEqual(
            comparison["rerun"]["selected_answer_correctness"],
            {"numerator": 3, "denominator": 3},
        )
        self.assertEqual(
            comparison["rerun"]["projected_full_answer_correctness"],
            {"numerator": 27, "denominator": 30},
        )
        self.assertEqual(comparison["rerun"]["correctness_delta"], 3)

    def test_revenue_rerun_supports_a_zero_success_subset_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            business = create_demo_database(root / "business.sqlite3")
            transport = NoNetworkTransport()
            generator = DeepSeekSqlGenerator(enabled=True, transport=transport)

            report = run_model_evaluation(
                DATASET_PATH,
                business_database=business,
                checkpoint_database=root / "workflow.sqlite3",
                generator=generator,
                evaluation_id="revenue-local",
                case_validator=validate_revenue_paraphrase_rerun_contract,
                case_loader=load_revenue_paraphrase_rerun_cases,
            )

        self.assertEqual(transport.calls, [])
        self.assertEqual(
            report["metrics"]["execution_success_rate"],
            {"numerator": 0, "denominator": 0, "value": None},
        )
        self.assertEqual(
            report["metrics"]["answer_correctness"],
            {"numerator": 3, "denominator": 3, "value": 1.0},
        )
        self.assertEqual(report["provider_usage"]["reported_case_count"], 0)
        self.assertEqual(report["safety"]["non_success_execution_attempts"], 0)


if __name__ == "__main__":
    unittest.main()
