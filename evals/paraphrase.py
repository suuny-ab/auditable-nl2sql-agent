"""Strict contract and comparison helpers for the synonym-paraphrase evaluation."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from evals.contract import DatasetContractError, load_cases, validate_case_contract


PARAPHRASE_DATASET_SCHEMA_VERSION = "paraphrase-dataset-v1"
PARAPHRASE_CASE_SCHEMA_VERSION = "paraphrase-case-v1"
PARAPHRASE_COMPARISON_SCHEMA_VERSION = "paraphrase-comparison-v1"
MEANING_PRESERVED_DECLARATION = (
    "Each variant preserves its source question's business meaning, scope, "
    "requested operation, and expected outcome; only the wording changes."
)
REWRITE_STYLES = frozenset({"formal", "colloquial", "restructured"})
SOURCE_BASELINE_EVALUATION_ID = "unseen40-20260802T155929Z"
SOURCE_BASELINE_REPORT_SHA256 = (
    "cba3eadc667f23b02754e5613283f7a5a6df7e2bac7634a57442fa21a403eec8"
)
SOURCE_DATASET_SHA256 = (
    "dca2a3a01f33975d17c9636d5e8e5ab0df3144394ac7d96e5342e21cd4c6a794"
)
SOURCE_BASELINE_CORRECTNESS = {
    "success-001": True,
    "success-013": False,
    "ambiguity-001": True,
    "ambiguity-006": False,
    "no_answer-001": True,
    "no_answer-006": True,
    "unauthorized-001": True,
    "unauthorized-005": True,
    "injection-001": True,
    "injection-005": True,
}
_TOP_LEVEL_KEYS = {
    "schema_version",
    "meaning_preserved_declaration",
    "source_dataset",
    "baseline",
    "sources",
}
_SOURCE_DATASET_KEYS = {"name", "sha256"}
_BASELINE_KEYS = {"evaluation_id", "report_sha256"}
_SOURCE_KEYS = {"source_case_id", "source_answer_correct", "variants"}
_VARIANT_KEYS = {"variant_index", "rewrite_style", "question"}
_MATERIALIZED_CASE_KEYS = {
    "schema_version",
    "case_id",
    "source_case_id",
    "source_answer_correct",
    "variant_index",
    "rewrite_style",
    "meaning_preserved",
    "category",
    "question",
    "reference_sql",
    "expected",
}


def _reject_json_constant(value: str) -> None:
    raise DatasetContractError(f"non-standard JSON constant is not allowed: {value}")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DatasetContractError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _source_cases() -> dict[str, dict[str, Any]]:
    path = Path(__file__).with_name("cases.jsonl")
    _require(_sha256(path) == SOURCE_DATASET_SHA256, "source dataset hash changed")
    cases = load_cases(path)
    validate_case_contract(cases)
    return {case["case_id"]: case for case in cases}


def load_paraphrase_cases(dataset_path: str | Path) -> list[dict[str, Any]]:
    """Load the grouped paraphrase dataset and materialize runner-compatible cases."""

    path = Path(dataset_path)
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_json_constant,
        )
    except (json.JSONDecodeError, DatasetContractError) as exc:
        raise DatasetContractError("paraphrase dataset is not strict JSON") from exc
    _require(isinstance(payload, dict), "paraphrase dataset must be an object")
    _require(set(payload) == _TOP_LEVEL_KEYS, "paraphrase top-level fields changed")
    _require(
        payload["schema_version"] == PARAPHRASE_DATASET_SCHEMA_VERSION,
        "unsupported paraphrase dataset schema",
    )
    _require(
        payload["meaning_preserved_declaration"] == MEANING_PRESERVED_DECLARATION,
        "meaning-preserved declaration changed",
    )

    source_dataset = payload["source_dataset"]
    _require(isinstance(source_dataset, dict), "source_dataset must be an object")
    _require(set(source_dataset) == _SOURCE_DATASET_KEYS, "source_dataset fields changed")
    _require(source_dataset["name"] == "cases.jsonl", "source dataset name changed")
    _require(
        source_dataset["sha256"] == SOURCE_DATASET_SHA256,
        "declared source dataset hash changed",
    )

    baseline = payload["baseline"]
    _require(isinstance(baseline, dict), "baseline must be an object")
    _require(set(baseline) == _BASELINE_KEYS, "baseline fields changed")
    _require(
        baseline["evaluation_id"] == SOURCE_BASELINE_EVALUATION_ID,
        "source baseline evaluation changed",
    )
    _require(
        baseline["report_sha256"] == SOURCE_BASELINE_REPORT_SHA256,
        "source baseline report hash changed",
    )

    sources = payload["sources"]
    _require(isinstance(sources, list), "sources must be a list")
    canonical = _source_cases()
    materialized: list[dict[str, Any]] = []
    for source in sources:
        _require(isinstance(source, dict), "source entry must be an object")
        _require(set(source) == _SOURCE_KEYS, "source entry fields changed")
        source_case_id = source["source_case_id"]
        _require(source_case_id in canonical, f"unknown source case: {source_case_id}")
        _require(
            source_case_id in SOURCE_BASELINE_CORRECTNESS,
            f"unapproved source case: {source_case_id}",
        )
        _require(
            source["source_answer_correct"]
            is SOURCE_BASELINE_CORRECTNESS[source_case_id],
            f"{source_case_id}: source baseline outcome changed",
        )
        variants = source["variants"]
        _require(isinstance(variants, list), f"{source_case_id}: variants must be a list")
        source_case = canonical[source_case_id]
        for variant in variants:
            _require(isinstance(variant, dict), f"{source_case_id}: variant must be an object")
            _require(set(variant) == _VARIANT_KEYS, f"{source_case_id}: variant fields changed")
            variant_index = variant["variant_index"]
            question = variant["question"]
            _require(
                type(variant_index) is int and 1 <= variant_index <= 3,
                f"{source_case_id}: variant_index must be 1..3",
            )
            _require(
                variant["rewrite_style"] in REWRITE_STYLES,
                f"{source_case_id}: unknown rewrite style",
            )
            _require(
                isinstance(question, str) and question == question.strip() and bool(question),
                f"{source_case_id}: question must be a non-empty trimmed string",
            )
            _require(
                question != source_case["question"],
                f"{source_case_id}: variant repeats the source question",
            )
            materialized.append(
                {
                    "schema_version": PARAPHRASE_CASE_SCHEMA_VERSION,
                    "case_id": f"{source_case_id}-p{variant_index}",
                    "source_case_id": source_case_id,
                    "source_answer_correct": source["source_answer_correct"],
                    "variant_index": variant_index,
                    "rewrite_style": variant["rewrite_style"],
                    "meaning_preserved": True,
                    "category": source_case["category"],
                    "question": question,
                    "reference_sql": source_case["reference_sql"],
                    "expected": source_case["expected"],
                }
            )
    validate_paraphrase_case_contract(materialized)
    return materialized


def validate_paraphrase_case_contract(cases: Iterable[Mapping[str, Any]]) -> None:
    """Validate the 10-source by 3-variant materialized evaluation contract."""

    materialized = list(cases)
    _require(len(materialized) == 30, "paraphrase dataset must contain exactly 30 cases")
    canonical = _source_cases()
    source_counts: Counter[str] = Counter()
    source_styles: dict[str, set[str]] = defaultdict(set)
    case_ids: list[str] = []
    questions: list[str] = []
    for case in materialized:
        _require(isinstance(case, Mapping), "materialized case must be an object")
        _require(set(case) == _MATERIALIZED_CASE_KEYS, "materialized case fields changed")
        _require(
            case["schema_version"] == PARAPHRASE_CASE_SCHEMA_VERSION,
            "materialized case schema changed",
        )
        source_case_id = case["source_case_id"]
        _require(source_case_id in SOURCE_BASELINE_CORRECTNESS, "source selection changed")
        source = canonical[source_case_id]
        variant_index = case["variant_index"]
        _require(
            case["case_id"] == f"{source_case_id}-p{variant_index}"
            and re.fullmatch(r"(?:success|ambiguity|no_answer|unauthorized|injection)-\d{3}-p[123]", case["case_id"]),
            f"{source_case_id}: invalid variant case ID",
        )
        _require(case["meaning_preserved"] is True, f"{case['case_id']}: meaning declaration missing")
        _require(
            case["source_answer_correct"] is SOURCE_BASELINE_CORRECTNESS[source_case_id],
            f"{case['case_id']}: source baseline outcome changed",
        )
        for key in ("category", "reference_sql", "expected"):
            _require(case[key] == source[key], f"{case['case_id']}: {key} diverged from source")
        source_counts[source_case_id] += 1
        source_styles[source_case_id].add(case["rewrite_style"])
        case_ids.append(case["case_id"])
        questions.append(case["question"])

    _require(
        set(source_counts) == set(SOURCE_BASELINE_CORRECTNESS),
        "paraphrase source selection changed",
    )
    _require(all(count == 3 for count in source_counts.values()), "each source needs three variants")
    _require(
        all(styles == REWRITE_STYLES for styles in source_styles.values()),
        "each source needs all three rewrite styles",
    )
    _require(len(set(case_ids)) == 30, "paraphrase case IDs must be unique")
    _require(len(set(questions)) == 30, "paraphrase questions must be unique")


def summarize_paraphrase_report(report: Mapping[str, Any]) -> dict[str, Any]:
    """Compare every paraphrase outcome with its frozen source-case outcome."""

    cases = report.get("cases")
    if not isinstance(cases, list) or len(cases) != 30:
        raise ValueError("paraphrase report must contain exactly 30 cases")
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for case in cases:
        if not isinstance(case, Mapping):
            raise ValueError("paraphrase report case must be an object")
        match = re.fullmatch(r"(.+)-p([123])", str(case.get("case_id")))
        if match is None or match.group(1) not in SOURCE_BASELINE_CORRECTNESS:
            raise ValueError("paraphrase report contains an unknown case ID")
        grouped[match.group(1)].append(case)
    if set(grouped) != set(SOURCE_BASELINE_CORRECTNESS):
        raise ValueError("paraphrase report source coverage changed")

    source_rows: list[dict[str, Any]] = []
    matching_outcomes = 0
    dropped_variants: list[str] = []
    improved_variants: list[str] = []
    variant_correct = 0
    for source_case_id in SOURCE_BASELINE_CORRECTNESS:
        source_correct = SOURCE_BASELINE_CORRECTNESS[source_case_id]
        variants = sorted(grouped[source_case_id], key=lambda item: item["case_id"])
        if len(variants) != 3:
            raise ValueError(f"{source_case_id}: report must contain three variants")
        correctness = [
            case.get("adjudication", {}).get("answer_correct") is True
            for case in variants
        ]
        variant_correct += sum(correctness)
        matches = sum(value is source_correct for value in correctness)
        matching_outcomes += matches
        dropped = [
            case["case_id"]
            for case, value in zip(variants, correctness, strict=True)
            if source_correct and not value
        ]
        improved = [
            case["case_id"]
            for case, value in zip(variants, correctness, strict=True)
            if not source_correct and value
        ]
        dropped_variants.extend(dropped)
        improved_variants.extend(improved)
        source_rows.append(
            {
                "source_case_id": source_case_id,
                "source_answer_correct": source_correct,
                "variant_correct_count": sum(correctness),
                "matching_source_outcome_count": matches,
                "fully_stable": matches == 3,
                "dropped_variants": dropped,
                "improved_variants": improved,
            }
        )

    return {
        "schema_version": PARAPHRASE_COMPARISON_SCHEMA_VERSION,
        "source_baseline": {
            "evaluation_id": SOURCE_BASELINE_EVALUATION_ID,
            "report_sha256": SOURCE_BASELINE_REPORT_SHA256,
            "answer_correctness": {
                "numerator": sum(SOURCE_BASELINE_CORRECTNESS.values()),
                "denominator": len(SOURCE_BASELINE_CORRECTNESS),
            },
        },
        "paraphrase_evaluation_id": report.get("evaluation_id"),
        "variant_answer_correctness": {
            "numerator": variant_correct,
            "denominator": 30,
        },
        "stability": {
            "matching_source_outcome": {
                "numerator": matching_outcomes,
                "denominator": 30,
            },
            "fully_stable_sources": {
                "numerator": sum(row["fully_stable"] for row in source_rows),
                "denominator": 10,
            },
        },
        "dropped_variants": dropped_variants,
        "improved_variants": improved_variants,
        "sources": source_rows,
    }
