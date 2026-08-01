from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from auditable_nl2sql.demo import create_demo_database
from evals.contract import (
    CATEGORY_COUNTS,
    DatasetContractError,
    load_cases,
    validate_case_contract,
    validate_reference_cases,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "evals" / "cases.jsonl"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EvaluationDatasetContractTests(unittest.TestCase):
    def test_dataset_has_exact_frozen_shape_and_category_counts(self) -> None:
        cases = load_cases(DATASET_PATH)

        validate_case_contract(cases)

        self.assertEqual(len(cases), 20)
        self.assertEqual(
            Counter(case["category"] for case in cases),
            Counter(CATEGORY_COUNTS),
        )
        self.assertEqual(len({case["case_id"] for case in cases}), 20)
        self.assertEqual(len({case["question"] for case in cases}), 20)

    def test_reference_sql_matches_workflow_without_business_mutation(self) -> None:
        cases = load_cases(DATASET_PATH)
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            business_database = create_demo_database(root / "business.sqlite3")
            checkpoint_database = root / "workflow.sqlite3"
            before = _sha256(business_database)

            validate_reference_cases(
                cases,
                business_database=business_database,
                checkpoint_database=checkpoint_database,
            )

            self.assertEqual(_sha256(business_database), before)

    def test_contract_rejects_unknown_fields_duplicates_and_nonstandard_json(self) -> None:
        cases = load_cases(DATASET_PATH)

        unknown_field = copy.deepcopy(cases)
        unknown_field[0]["unexpected"] = True
        with self.assertRaises(DatasetContractError):
            validate_case_contract(unknown_field)

        duplicate_id = copy.deepcopy(cases)
        duplicate_id[1]["case_id"] = duplicate_id[0]["case_id"]
        with self.assertRaises(DatasetContractError):
            validate_case_contract(duplicate_id)

        with tempfile.TemporaryDirectory() as temporary_directory:
            invalid_path = Path(temporary_directory) / "invalid.jsonl"
            invalid_path.write_text('{"value":NaN}\n', encoding="utf-8")
            with self.assertRaises(DatasetContractError):
                load_cases(invalid_path)


if __name__ == "__main__":
    unittest.main()
