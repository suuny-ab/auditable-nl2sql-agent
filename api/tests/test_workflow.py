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

from auditable_nl2sql import (
    CANONICAL_QUESTION,
    DuplicateRunError,
    WorkflowRunner,
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

        self.assertEqual(record["schema_version"], "run-record-v1")
        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["query_columns"], ["revenue"])
        self.assertEqual(record["query_rows"], [[5946.0]])
        self.assertEqual(record["attempt_count"], 1)
        self.assertIsNone(record["error_code"])
        self.assertEqual(
            [event["node"] for event in record["trajectory"]],
            ["load_schema", "draft_sql", "execute_sql", "finish"],
        )
        self.assertEqual(
            [event["sequence"] for event in record["trajectory"]],
            [1, 2, 3, 4],
        )
        self.assertGreaterEqual(record["checkpoint_count"], 5)
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
        self.assertEqual(
            [event["node"] for event in record["trajectory"]],
            ["load_schema", "draft_sql", "execute_sql"],
        )
        self.assertEqual(record["trajectory"][-1]["status"], "failed")
        self.assertEqual(_sha256(self.business_database), before)

    def test_read_only_violation_is_persisted_without_mutation(self) -> None:
        before = _sha256(self.business_database)

        with WorkflowRunner(
            self.business_database,
            self.checkpoint_database,
            generator=MutatingSqlGenerator(),
        ) as runner:
            record = runner.run(
                run_id="write-denied-001",
                question="force write SQL",
            )

        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["error_code"], "read_only_violation")
        self.assertEqual(record["attempt_count"], 1)
        self.assertEqual(record["trajectory"][-1]["node"], "execute_sql")
        self.assertEqual(_sha256(self.business_database), before)

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
from auditable_nl2sql import WorkflowRunner

class MustNotRun:
    def generate(self, question: str, schema_snapshot: list[dict[str, Any]]) -> str:
        raise AssertionError("get_run must not execute graph nodes")

with WorkflowRunner(sys.argv[1], sys.argv[2], generator=MustNotRun()) as runner:
    print(json.dumps(runner.get_run("restart-001"), ensure_ascii=False, sort_keys=True))
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


if __name__ == "__main__":
    unittest.main()
