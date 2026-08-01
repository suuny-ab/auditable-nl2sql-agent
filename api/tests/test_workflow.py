from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from typing import Any
from unittest.mock import patch

from auditable_nl2sql import (
    AnswerCompositionError,
    CANONICAL_QUESTION,
    DuplicateRunError,
    InvalidApprovalDecisionError,
    RunNotFoundError,
    StaticSqlGenerator,
    WorkflowRunner,
    verify_evidence,
)
from auditable_nl2sql.demo import create_demo_database


class InvalidSqlGenerator:
    def generate(self, question: str, schema_snapshot: list[dict[str, Any]]) -> str:
        del question, schema_snapshot
        return "SELECT missing_column FROM missing_table"


class MutatingSqlGenerator:
    def generate(self, question: str, schema_snapshot: list[dict[str, Any]]) -> str:
        del question, schema_snapshot
        return "DELETE FROM orders WHERE order_id = 'O1001'"


class MustNotGenerate:
    def generate(self, question: str, schema_snapshot: list[dict[str, Any]]) -> str:
        del question, schema_snapshot
        raise AssertionError("resuming or reading a run must not generate SQL again")


HIGH_ROW_QUESTION = "列出六条订单商品记录"
HIGH_ROW_SQL = (
    "SELECT order_id, product_id FROM order_items "
    "ORDER BY order_id, product_id LIMIT 6"
)
TRUNCATED_QUESTION = "列出十一条订单商品记录"
TRUNCATED_SQL = (
    "SELECT order_id, product_id FROM order_items "
    "ORDER BY order_id, product_id LIMIT 11"
)
EMPTY_QUESTION = "查询不存在的订单"
EMPTY_SQL = "SELECT order_id FROM orders WHERE order_id = 'missing' LIMIT 1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class WorkflowRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        root = Path(self.temporary_directory.name)
        self.business_database = create_demo_database(root / "business.sqlite3")
        self.checkpoint_database = root / "workflow.sqlite3"

    def test_success_run_is_auditable_and_keeps_business_database_unchanged(self) -> None:
        before = _sha256(self.business_database)

        with WorkflowRunner(
            self.business_database,
            self.checkpoint_database,
        ) as runner:
            record = runner.run(
                run_id="success-001",
                question=CANONICAL_QUESTION,
            )

        self.assertEqual(record["schema_version"], "run-record-v5")
        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["query_columns"], ["revenue"])
        self.assertEqual(record["query_rows"], [[5946.0]])
        self.assertEqual(record["attempt_count"], 1)
        self.assertIsNone(record["error_code"])
        self.assertIsNone(record["approval"])
        self.assertEqual(record["result_row_limit"], 100)
        self.assertEqual(record["result_validation"]["status"], "passed")
        self.assertTrue(verify_evidence(record["evidence"]))
        self.assertEqual(record["evidence"]["payload"]["run_id"], "success-001")
        self.assertEqual(record["answer"]["schema_version"], "answer-v1")
        self.assertEqual(record["answer"]["text"], "查询结果：revenue = 5946.0。")
        self.assertEqual(
            record["answer"]["source"]["evidence_fingerprint"],
            record["evidence"]["fingerprint"]["value"],
        )
        self.assertEqual(
            [event["node"] for event in record["trajectory"]],
            [
                "load_schema",
                "draft_sql",
                "assess_sql",
                "execute_sql",
                "validate_result",
                "bind_evidence",
                "compose_answer",
                "finish",
            ],
        )
        self.assertEqual(
            [event["sequence"] for event in record["trajectory"]],
            [1, 2, 3, 4, 5, 6, 7, 8],
        )
        self.assertGreaterEqual(record["checkpoint_count"], 9)
        json.dumps(record, allow_nan=False, ensure_ascii=False)
        self.assertEqual(_sha256(self.business_database), before)

        with closing(sqlite3.connect(self.business_database)) as connection:
            business_tables = [
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name"
                )
            ]
        self.assertEqual(
            business_tables,
            ["customers", "order_items", "orders", "products"],
        )

        with closing(sqlite3.connect(self.checkpoint_database)) as connection:
            workflow_tables = [
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name"
                )
            ]
        self.assertEqual(workflow_tables, ["checkpoints", "writes"])

    def test_execution_failure_is_persisted_without_retry_or_mutation(self) -> None:
        before = _sha256(self.business_database)

        with WorkflowRunner(
            self.business_database,
            self.checkpoint_database,
            generator=InvalidSqlGenerator(),
        ) as runner:
            record = runner.run(
                run_id="failure-001",
                question="force invalid SQL",
            )

        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["error_code"], "query_execution_error")
        self.assertEqual(record["attempt_count"], 1)
        self.assertEqual(record["query_rows"], [])
        self.assertIsNone(record["evidence"])
        self.assertIsNone(record["answer"])
        self.assertEqual(
            [event["node"] for event in record["trajectory"]],
            ["load_schema", "draft_sql", "assess_sql", "execute_sql"],
        )
        self.assertEqual(record["trajectory"][-1]["status"], "failed")
        self.assertEqual(_sha256(self.business_database), before)

    def test_approval_cannot_override_read_only_violation(self) -> None:
        before = _sha256(self.business_database)

        with WorkflowRunner(
            self.business_database,
            self.checkpoint_database,
            generator=MutatingSqlGenerator(),
        ) as runner:
            pending = runner.run(
                run_id="write-denied-001",
                question="force write SQL",
            )
            record = runner.decide(
                run_id="write-denied-001",
                decision_id="approve-write-001",
                approved=True,
            )

        self.assertEqual(pending["status"], "pending_approval")
        self.assertEqual(pending["attempt_count"], 0)
        self.assertEqual(pending["approval"]["reason"], "read_only_violation")
        self.assertFalse(pending["approval"]["can_execute"])
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["error_code"], "approval_cannot_override_read_only")
        self.assertEqual(record["attempt_count"], 0)
        self.assertEqual(record["query_rows"], [])
        self.assertIsNone(record["evidence"])
        self.assertIsNone(record["answer"])
        self.assertEqual(record["approval"]["decision"], "approved")
        self.assertEqual(record["trajectory"][-1]["node"], "approval_gate")
        self.assertEqual(_sha256(self.business_database), before)

    def test_high_row_approval_resumes_once_in_a_second_python_process(self) -> None:
        before = _sha256(self.business_database)
        generator = StaticSqlGenerator({HIGH_ROW_QUESTION: HIGH_ROW_SQL})
        with WorkflowRunner(
            self.business_database,
            self.checkpoint_database,
            generator=generator,
        ) as runner:
            pending = runner.run(
                run_id="high-row-001",
                question=HIGH_ROW_QUESTION,
            )

        self.assertEqual(pending["status"], "pending_approval")
        self.assertEqual(pending["attempt_count"], 0)
        self.assertEqual(pending["query_rows"], [])
        self.assertEqual(
            pending["approval"],
            {
                "required": True,
                "reason": "row_limit_exceeded",
                "threshold": 5,
                "requested_row_limit": 6,
                "can_execute": True,
                "decision": None,
                "decision_id": None,
            },
        )

        source_root = Path(__file__).resolve().parents[1] / "src"
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(source_root)
        script = """
import json
import sys
from typing import Any
from auditable_nl2sql import WorkflowRunner

class MustNotRun:
    def generate(self, question: str, schema_snapshot: list[dict[str, Any]]) -> str:
        raise AssertionError("resume must not execute the generator")

with WorkflowRunner(sys.argv[1], sys.argv[2], generator=MustNotRun()) as runner:
    record = runner.decide(
        run_id="high-row-001",
        decision_id="approve-high-row-001",
        approved=True,
    )
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))
"""
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                script,
                str(self.business_database),
                str(self.checkpoint_database),
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
        )
        approved = json.loads(completed.stdout)

        self.assertEqual(approved["status"], "completed")
        self.assertEqual(approved["attempt_count"], 1)
        self.assertEqual(len(approved["query_rows"]), 6)
        self.assertTrue(verify_evidence(approved["evidence"]))
        self.assertEqual(
            approved["answer"]["text"],
            "查询返回 6 行，字段：order_id、product_id。",
        )
        self.assertEqual(approved["approval"]["decision"], "approved")
        self.assertEqual(
            approved["approval"]["decision_id"],
            "approve-high-row-001",
        )
        self.assertEqual(
            [event["node"] for event in approved["trajectory"]],
            [
                "load_schema",
                "draft_sql",
                "assess_sql",
                "approval_gate",
                "execute_sql",
                "validate_result",
                "bind_evidence",
                "compose_answer",
                "finish",
            ],
        )

        with WorkflowRunner(
            self.business_database,
            self.checkpoint_database,
            generator=MustNotGenerate(),
        ) as runner:
            before_duplicate = runner.get_run("high-row-001")
            with self.assertRaises(InvalidApprovalDecisionError):
                runner.decide(
                    run_id="high-row-001",
                    decision_id="approve-high-row-001",
                    approved=True,
                )
            self.assertEqual(runner.get_run("high-row-001"), before_duplicate)

        self.assertEqual(_sha256(self.business_database), before)

    def test_rejection_and_invalid_decisions_fail_closed(self) -> None:
        before = _sha256(self.business_database)
        generator = StaticSqlGenerator({HIGH_ROW_QUESTION: HIGH_ROW_SQL})
        with WorkflowRunner(
            self.business_database,
            self.checkpoint_database,
            generator=generator,
        ) as runner:
            runner.run(run_id="reject-001", question=HIGH_ROW_QUESTION)
            with self.assertRaises(InvalidApprovalDecisionError):
                runner.decide(
                    run_id="reject-001",
                    decision_id="reject-001",
                    approved=1,  # type: ignore[arg-type]
                )
            with self.assertRaises(InvalidApprovalDecisionError):
                runner.decide(
                    run_id="reject-001",
                    decision_id="bad decision id",
                    approved=False,
                )
            with self.assertRaises(InvalidApprovalDecisionError):
                runner.decide(
                    run_id="reject-001",
                    decision_id=1,  # type: ignore[arg-type]
                    approved=False,
                )

            rejected = runner.decide(
                run_id="reject-001",
                decision_id="reject-high-row-001",
                approved=False,
            )
            with self.assertRaises(InvalidApprovalDecisionError):
                runner.decide(
                    run_id="reject-001",
                    decision_id="reject-high-row-002",
                    approved=False,
                )
            with self.assertRaises(RunNotFoundError):
                runner.decide(
                    run_id="missing-run",
                    decision_id="reject-missing-001",
                    approved=False,
                )

        self.assertEqual(rejected["status"], "rejected")
        self.assertEqual(rejected["error_code"], "approval_rejected")
        self.assertEqual(rejected["attempt_count"], 0)
        self.assertEqual(rejected["query_rows"], [])
        self.assertIsNone(rejected["evidence"])
        self.assertIsNone(rejected["answer"])
        self.assertEqual(rejected["approval"]["decision"], "rejected")
        self.assertEqual(rejected["trajectory"][-1]["node"], "approval_gate")
        self.assertEqual(_sha256(self.business_database), before)

    def test_conservative_row_limit_policy_has_explicit_boundaries(self) -> None:
        bounded_question = "列出五条订单"
        unbounded_question = "列出全部订单"
        generator = StaticSqlGenerator(
            {
                bounded_question: (
                    "SELECT order_id FROM orders ORDER BY order_id LIMIT 5"
                ),
                unbounded_question: "SELECT order_id FROM orders ORDER BY order_id",
            }
        )
        with WorkflowRunner(
            self.business_database,
            self.checkpoint_database,
            generator=generator,
        ) as runner:
            bounded = runner.run(run_id="bounded-001", question=bounded_question)
            unbounded = runner.run(run_id="unbounded-001", question=unbounded_question)

        self.assertEqual(bounded["status"], "completed")
        self.assertEqual(len(bounded["query_rows"]), 5)
        self.assertTrue(verify_evidence(bounded["evidence"]))
        self.assertEqual(
            bounded["answer"]["text"],
            "查询返回 5 行，字段：order_id。",
        )
        self.assertIsNone(bounded["approval"])
        self.assertEqual(unbounded["status"], "pending_approval")
        self.assertEqual(unbounded["attempt_count"], 0)
        self.assertEqual(unbounded["approval"]["reason"], "row_limit_unbounded")

    def test_unsupported_question_stops_before_sql_execution(self) -> None:
        with WorkflowRunner(
            self.business_database,
            self.checkpoint_database,
        ) as runner:
            record = runner.run(
                run_id="unsupported-001",
                question="这条问题没有 stub",
            )

        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["error_code"], "unsupported_question")
        self.assertEqual(record["attempt_count"], 0)
        self.assertIsNone(record["generated_sql"])
        self.assertIsNone(record["evidence"])
        self.assertIsNone(record["answer"])
        self.assertEqual(
            [event["node"] for event in record["trajectory"]],
            ["load_schema", "draft_sql"],
        )

    def test_missing_business_database_is_a_persisted_failure(self) -> None:
        missing_database = Path(self.temporary_directory.name) / "missing.sqlite3"
        with WorkflowRunner(
            missing_database,
            self.checkpoint_database,
        ) as runner:
            record = runner.run(
                run_id="missing-schema-001",
                question=CANONICAL_QUESTION,
            )

        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["error_code"], "schema_unavailable")
        self.assertEqual(record["attempt_count"], 0)
        self.assertIsNone(record["evidence"])
        self.assertIsNone(record["answer"])
        self.assertEqual(
            [event["node"] for event in record["trajectory"]],
            ["load_schema"],
        )

    def test_second_python_process_reads_run_without_executing_nodes(self) -> None:
        with WorkflowRunner(
            self.business_database,
            self.checkpoint_database,
        ) as runner:
            original = runner.run(
                run_id="restart-001",
                question=CANONICAL_QUESTION,
            )

        source_root = Path(__file__).resolve().parents[1] / "src"
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(source_root)
        script = """
import json
import sys
from typing import Any
from auditable_nl2sql import WorkflowRunner, verify_evidence

class MustNotRun:
    def generate(self, question: str, schema_snapshot: list[dict[str, Any]]) -> str:
        raise AssertionError("get_run must not execute graph nodes")

with WorkflowRunner(sys.argv[1], sys.argv[2], generator=MustNotRun()) as runner:
    record = runner.get_run("restart-001")
    if not verify_evidence(record["evidence"]):
        raise AssertionError("persisted evidence fingerprint did not verify")
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))
"""
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                script,
                str(self.business_database),
                str(self.checkpoint_database),
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
        )
        reopened = json.loads(completed.stdout)

        self.assertEqual(reopened, original)
        self.assertEqual(reopened["status"], "completed")
        self.assertEqual(reopened["query_rows"], [[5946.0]])
        self.assertTrue(verify_evidence(reopened["evidence"]))
        self.assertEqual(reopened["answer"], original["answer"])

    def test_empty_result_produces_a_conservative_answer(self) -> None:
        generator = StaticSqlGenerator({EMPTY_QUESTION: EMPTY_SQL})
        with WorkflowRunner(
            self.business_database,
            self.checkpoint_database,
            generator=generator,
        ) as runner:
            record = runner.run(run_id="empty-001", question=EMPTY_QUESTION)

        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["query_rows"], [])
        self.assertEqual(record["answer"]["text"], "查询未返回数据。")
        self.assertEqual(
            record["answer"]["source"]["references"],
            [
                {
                    "kind": "result_metadata",
                    "path": "payload.result.returned_row_count",
                    "value": 0,
                }
            ],
        )

    def test_answer_composition_failure_is_persisted_without_answer(self) -> None:
        before = _sha256(self.business_database)
        failure = AnswerCompositionError(
            code="evidence_verification_failed",
            message="evidence fingerprint verification failed",
        )
        with patch("auditable_nl2sql.workflow.compose_answer", side_effect=failure):
            with WorkflowRunner(
                self.business_database,
                self.checkpoint_database,
            ) as runner:
                record = runner.run(
                    run_id="answer-failure-001",
                    question=CANONICAL_QUESTION,
                )

        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["error_code"], "evidence_verification_failed")
        self.assertTrue(verify_evidence(record["evidence"]))
        self.assertIsNone(record["answer"])
        self.assertEqual(record["trajectory"][-1]["node"], "compose_answer")
        self.assertEqual(record["trajectory"][-1]["status"], "failed")
        self.assertEqual(_sha256(self.business_database), before)

    def test_truncated_result_fails_validation_without_evidence(self) -> None:
        before = _sha256(self.business_database)
        generator = StaticSqlGenerator({TRUNCATED_QUESTION: TRUNCATED_SQL})
        with WorkflowRunner(
            self.business_database,
            self.checkpoint_database,
            generator=generator,
            max_result_rows=5,
        ) as runner:
            pending = runner.run(
                run_id="truncated-001",
                question=TRUNCATED_QUESTION,
            )

        self.assertEqual(pending["status"], "pending_approval")

        with WorkflowRunner(
            self.business_database,
            self.checkpoint_database,
            generator=MustNotGenerate(),
            max_result_rows=100,
        ) as runner:
            record = runner.decide(
                run_id="truncated-001",
                decision_id="approve-truncated-001",
                approved=True,
            )

        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["error_code"], "result_truncated")
        self.assertEqual(record["result_row_limit"], 5)
        self.assertEqual(len(record["query_rows"]), 5)
        self.assertTrue(record["truncated"])
        self.assertEqual(record["result_validation"]["status"], "failed")
        self.assertIsNone(record["evidence"])
        self.assertIsNone(record["answer"])
        self.assertEqual(record["trajectory"][-1]["node"], "validate_result")
        self.assertEqual(record["attempt_count"], 1)
        self.assertEqual(_sha256(self.business_database), before)

    def test_duplicate_run_and_shared_database_path_fail_closed(self) -> None:
        with WorkflowRunner(
            self.business_database,
            self.checkpoint_database,
        ) as runner:
            runner.run(run_id="unique-001", question=CANONICAL_QUESTION)
            with self.assertRaises(DuplicateRunError):
                runner.run(run_id="unique-001", question=CANONICAL_QUESTION)

        with self.assertRaises(ValueError):
            WorkflowRunner(self.business_database, self.business_database)
        with self.assertRaises(ValueError):
            WorkflowRunner(
                self.business_database,
                self.checkpoint_database,
                approval_row_limit=0,
            )
        with self.assertRaises(ValueError):
            WorkflowRunner(
                self.business_database,
                self.checkpoint_database,
                max_result_rows=0,
            )


if __name__ == "__main__":
    unittest.main()
