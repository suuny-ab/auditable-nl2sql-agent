from __future__ import annotations

import copy
import hashlib
import json
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
ORIGINAL_CASE_IDS = frozenset(
    {
        *(f"success-{index:03d}" for index in range(1, 9)),
        *(f"ambiguity-{index:03d}" for index in range(1, 4)),
        *(f"no_answer-{index:03d}" for index in range(1, 4)),
        *(f"unauthorized-{index:03d}" for index in range(1, 4)),
        *(f"injection-{index:03d}" for index in range(1, 4)),
    }
)
ORIGINAL_CASES_CANONICAL_SHA256 = (
    "773d0eaeb83060e40b3fd8119ac4738f5b494a8030f8d5d9659c71c57b5864e4"
)
NEW_CASE_IDS = frozenset(
    {
        *(f"success-{index:03d}" for index in range(9, 13)),
        *(f"ambiguity-{index:03d}" for index in range(4, 6)),
        *(f"no_answer-{index:03d}" for index in range(4, 6)),
        "unauthorized-004",
        "injection-004",
    }
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EvaluationDatasetContractTests(unittest.TestCase):
    def test_dataset_has_exact_frozen_shape_and_category_counts(self) -> None:
        cases = load_cases(DATASET_PATH)

        validate_case_contract(cases)

        self.assertEqual(len(cases), 30)
        self.assertEqual(
            Counter(case["category"] for case in cases),
            Counter(CATEGORY_COUNTS),
        )
        self.assertEqual(len({case["case_id"] for case in cases}), 30)
        self.assertEqual(len({case["question"] for case in cases}), 30)

        original_cases = [
            case for case in cases if case["case_id"] in ORIGINAL_CASE_IDS
        ]
        canonical = "\n".join(
            json.dumps(
                case,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            for case in original_cases
        ) + "\n"
        self.assertEqual(
            hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            ORIGINAL_CASES_CANONICAL_SHA256,
        )

        new_cases = [case for case in cases if case["case_id"] in NEW_CASE_IDS]
        self.assertEqual({case["case_id"] for case in new_cases}, NEW_CASE_IDS)
        for case in new_cases:
            if case["category"] in {"no_answer", "unauthorized"}:
                self.assertIsNone(case["reference_sql"])

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
