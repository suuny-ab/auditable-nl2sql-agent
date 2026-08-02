from __future__ import annotations

import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

import httpx

from auditable_nl2sql import (
    CANONICAL_QUESTION,
    CANONICAL_SQL,
    StaticSqlGenerator,
    WorkflowRunReader,
    WorkflowRunner,
)
from auditable_nl2sql.api import create_app
from auditable_nl2sql.demo import create_demo_database


SECOND_QUESTION = "列出六条订单商品记录"
SECOND_SQL = (
    "SELECT order_id, product_id FROM order_items "
    "ORDER BY order_id, product_id LIMIT 6"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReadOnlyApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        root = Path(self.temporary_directory.name)
        self.root = root
        self.business_database = create_demo_database(root / "business.sqlite3")
        self.checkpoint_database = root / "workflow.sqlite3"
        generator = StaticSqlGenerator(
            {
                CANONICAL_QUESTION: (
                    CANONICAL_SQL
                ),
                SECOND_QUESTION: SECOND_SQL,
            }
        )
        with WorkflowRunner(
            self.business_database,
            self.checkpoint_database,
            generator=generator,
        ) as runner:
            self.completed = runner.run(
                run_id="completed-run",
                question=CANONICAL_QUESTION,
            )
            self.pending = runner.run(
                run_id="pending-run",
                question=SECOND_QUESTION,
            )
        self.business_after_write_sha256 = _sha256(self.business_database)
        self.checkpoint_after_write_sha256 = _sha256(self.checkpoint_database)
        self.reader = WorkflowRunReader(
            self.business_database,
            self.checkpoint_database,
        )
        self.addCleanup(self.reader.close)
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(self.reader)),
            base_url="http://testserver",
        )
        self.addAsyncCleanup(self.client.aclose)

    async def test_list_returns_stable_newest_first_summaries_and_pagination(
        self,
    ) -> None:
        response = await self.client.get(
            "/api/v1/runs", params={"limit": 1, "offset": 0}
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["schema_version"], "run-list-v1")
        self.assertEqual(payload["total"], 2)
        self.assertEqual(payload["limit"], 1)
        self.assertEqual(payload["offset"], 0)
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["run_id"], "pending-run")
        self.assertEqual(payload["items"][0]["status"], "pending_approval")
        self.assertTrue(payload["items"][0]["approval_required"])
        self.assertEqual(
            payload["items"][0]["trajectory_length"],
            len(self.pending["trajectory"]),
        )

        second_page = await self.client.get(
            "/api/v1/runs", params={"limit": 1, "offset": 1}
        )
        second_page = second_page.json()
        self.assertEqual(second_page["items"][0]["run_id"], "completed-run")

    async def test_health_reports_versioned_read_only_service(self) -> None:
        response = await self.client.get("/api/v1/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "schema_version": "health-v1",
                "status": "ok",
                "version": "0.1.0.dev0",
                "read_only": True,
            },
        )
        rejected = await self.client.post("/api/v1/health")
        self.assertEqual(rejected.status_code, 405)

    async def test_detail_reuses_complete_run_record_and_maps_errors(self) -> None:
        response = await self.client.get("/api/v1/runs/completed-run")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self.completed)
        self.assertEqual(response.json()["schema_version"], "run-record-v5")
        self.assertEqual(
            [event["sequence"] for event in response.json()["trajectory"]],
            list(range(1, len(self.completed["trajectory"]) + 1)),
        )

        missing = await self.client.get("/api/v1/runs/missing-run")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"detail": "run not found"})

        invalid = await self.client.get("/api/v1/runs/bad!id")
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(invalid.json(), {"detail": "invalid run_id"})

    async def test_queries_and_rejections_leave_both_databases_unchanged(
        self,
    ) -> None:
        business_before = _sha256(self.business_database)
        checkpoint_before = _sha256(self.checkpoint_database)
        self.assertEqual(business_before, self.business_after_write_sha256)
        self.assertEqual(checkpoint_before, self.checkpoint_after_write_sha256)
        completed_before = self.reader.get_run("completed-run")
        pending_before = self.reader.get_run("pending-run")

        responses = [
            await self.client.get("/api/v1/runs"),
            await self.client.get("/api/v1/runs/completed-run"),
            await self.client.get("/api/v1/runs/missing-run"),
            await self.client.get("/api/v1/runs/bad!id"),
            await self.client.get("/api/v1/runs", params={"limit": 0}),
            await self.client.get("/api/v1/runs", params={"limit": 101}),
            await self.client.get("/api/v1/runs", params={"offset": -1}),
            await self.client.post("/api/v1/runs"),
            await self.client.post("/api/v1/runs/completed-run"),
        ]

        self.assertEqual(
            [response.status_code for response in responses],
            [200, 200, 404, 422, 422, 422, 422, 405, 405],
        )
        self.assertEqual(self.reader.get_run("completed-run"), completed_before)
        self.assertEqual(self.reader.get_run("pending-run"), pending_before)
        self.assertEqual(_sha256(self.business_database), business_before)
        self.assertEqual(_sha256(self.checkpoint_database), checkpoint_before)

    def test_reader_has_no_mutating_surface_and_checkpoint_rejects_writes(self) -> None:
        self.assertFalse(hasattr(self.reader, "run"))
        self.assertFalse(hasattr(self.reader, "decide"))
        with self.assertRaisesRegex(sqlite3.OperationalError, "readonly"):
            self.reader._runner._connection.execute("DELETE FROM checkpoints")
        self.assertEqual(
            _sha256(self.checkpoint_database),
            self.checkpoint_after_write_sha256,
        )

        missing_checkpoint = self.root / "missing-checkpoint.sqlite3"
        with self.assertRaisesRegex(ValueError, "must already exist"):
            WorkflowRunReader(self.business_database, missing_checkpoint)
        self.assertFalse(missing_checkpoint.exists())


if __name__ == "__main__":
    unittest.main()
