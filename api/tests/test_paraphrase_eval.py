from __future__ import annotations

import copy
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from auditable_nl2sql.demo import create_demo_database
from evals.contract import DatasetContractError, validate_reference_cases
from evals.paraphrase import (
    REWRITE_STYLES,
    SOURCE_BASELINE_CORRECTNESS,
    load_paraphrase_cases,
    summarize_paraphrase_report,
    validate_paraphrase_case_contract,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "evals" / "paraphrase_cases.json"


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


if __name__ == "__main__":
    unittest.main()
