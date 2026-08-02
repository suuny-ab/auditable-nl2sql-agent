from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import httpx

from auditable_nl2sql import CANONICAL_QUESTION, WorkflowRunner
from auditable_nl2sql.demo import create_demo_database
from auditable_nl2sql.server import create_runtime_app


API_ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


class RuntimeApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        root = Path(self.temporary_directory.name)
        self.business_database = create_demo_database(root / "business.sqlite3")
        self.checkpoint_database = root / "workflow.sqlite3"
        with WorkflowRunner(
            self.business_database,
            self.checkpoint_database,
        ) as runner:
            self.completed = runner.run(
                run_id="health-smoke-run",
                question=CANONICAL_QUESTION,
            )
        self.business_sha256 = _sha256(self.business_database)
        self.checkpoint_sha256 = _sha256(self.checkpoint_database)

    async def test_lifespan_opens_and_closes_read_only_reader(self) -> None:
        app = create_runtime_app(
            self.business_database,
            self.checkpoint_database,
        )

        async with app.router.lifespan_context(app):
            run_reader = app.state.run_reader
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                health = await client.get("/api/v1/health")
                detail = await client.get("/api/v1/runs/health-smoke-run")

            self.assertEqual(health.status_code, 200)
            self.assertTrue(health.json()["read_only"])
            self.assertEqual(detail.json(), self.completed)

        with self.assertRaisesRegex(RuntimeError, "workflow runner is closed"):
            run_reader.list_runs()
        self.assertEqual(_sha256(self.business_database), self.business_sha256)
        self.assertEqual(_sha256(self.checkpoint_database), self.checkpoint_sha256)

    def test_missing_database_fails_without_creating_file(self) -> None:
        missing_business = self.business_database.parent / "missing-business.sqlite3"
        missing_checkpoint = self.business_database.parent / "missing-workflow.sqlite3"

        with self.assertRaisesRegex(ValueError, "business database must already exist"):
            create_runtime_app(missing_business, self.checkpoint_database)
        with self.assertRaisesRegex(ValueError, "checkpoint database must already exist"):
            create_runtime_app(self.business_database, missing_checkpoint)

        self.assertFalse(missing_business.exists())
        self.assertFalse(missing_checkpoint.exists())

    def test_documented_module_command_starts_real_http_server(self) -> None:
        port = _available_port()
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(API_ROOT / "src")
        command = [
            sys.executable,
            "-m",
            "auditable_nl2sql.server",
            "--business-database",
            str(self.business_database),
            "--checkpoint-database",
            str(self.checkpoint_database),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ]
        process = subprocess.Popen(
            command,
            cwd=API_ROOT.parent,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(self._stop_process, process)
        health_url = f"http://127.0.0.1:{port}/api/v1/health"

        payload = self._wait_for_json(process, health_url)

        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["read_only"])
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/v1/runs/health-smoke-run",
            timeout=2,
        ) as response:
            self.assertEqual(json.load(response), self.completed)
        self.assertEqual(_sha256(self.business_database), self.business_sha256)
        self.assertEqual(_sha256(self.checkpoint_database), self.checkpoint_sha256)

    def _wait_for_json(
        self,
        process: subprocess.Popen[str],
        url: str,
    ) -> dict[str, object]:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                self.fail(
                    f"server exited with {process.returncode}\nstdout={stdout}\nstderr={stderr}"
                )
            try:
                with urllib.request.urlopen(url, timeout=1) as response:
                    return json.load(response)
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.05)
        self.fail("server did not become healthy within 10 seconds")

    @staticmethod
    def _stop_process(process: subprocess.Popen[str]) -> None:
        if process.poll() is None:
            process.terminate()
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main()
