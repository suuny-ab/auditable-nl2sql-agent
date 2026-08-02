from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from auditable_nl2sql import WorkflowRunReader

from deploy.create_synthetic_fixture import (
    CONTAINER_DEMO_RUN_ID,
    create_synthetic_fixture,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ContainerContractTests(unittest.TestCase):
    def test_synthetic_fixture_contains_one_completed_read_only_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            fixture_root = Path(temporary_directory) / "fixture"
            business_database, checkpoint_database = create_synthetic_fixture(
                fixture_root,
            )
            business_sha256 = _sha256(business_database)
            checkpoint_sha256 = _sha256(checkpoint_database)

            with WorkflowRunReader(
                business_database,
                checkpoint_database,
            ) as reader:
                listing = reader.list_runs()
                record = reader.get_run(CONTAINER_DEMO_RUN_ID)

            self.assertEqual(listing["total"], 1)
            self.assertEqual(record["schema_version"], "run-record-v5")
            self.assertEqual(record["run_id"], CONTAINER_DEMO_RUN_ID)
            self.assertEqual(record["status"], "completed")
            self.assertEqual(_sha256(business_database), business_sha256)
            self.assertEqual(_sha256(checkpoint_database), checkpoint_sha256)

    def test_docker_compose_and_ci_keep_the_runtime_read_only(self) -> None:
        dockerfile = (REPOSITORY_ROOT / "deploy" / "Dockerfile").read_text(
            encoding="utf-8"
        )
        compose = (REPOSITORY_ROOT / "compose.yaml").read_text(encoding="utf-8")
        workflow = (
            REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
        ).read_text(encoding="utf-8")
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        fixture = (
            REPOSITORY_ROOT / "deploy" / "create_synthetic_fixture.py"
        ).read_text(encoding="utf-8")
        entrypoint = (
            REPOSITORY_ROOT / "deploy" / "container-entrypoint.sh"
        ).read_text(encoding="utf-8")

        for required in (
            "python:3.13-slim-bookworm@sha256:",
            "--require-hashes",
            "USER 10001:10001",
            "HEALTHCHECK",
            "create_synthetic_fixture.py",
        ):
            with self.subTest(dockerfile=required):
                self.assertIn(required, dockerfile)
        for required in (
            "read_only: true",
            "no-new-privileges:true",
            "cap_drop:",
            "127.0.0.1:${AUDITABLE_NL2SQL_API_PORT:-8000}:8000",
        ):
            with self.subTest(compose=required):
                self.assertIn(required, compose)
        self.assertIn('CONTAINER_DEMO_RUN_ID = "container-demo-run"', fixture)
        self.assertIn("/tmp/auditable-nl2sql-data", entrypoint)
        self.assertIn("chmod 0444", entrypoint)
        self.assertNotIn("DEEPSEEK_API_KEY", dockerfile + compose)
        self.assertIn("docker compose up --build --detach --wait", workflow)
        self.assertIn("docker compose up --build --detach --wait", readme)


if __name__ == "__main__":
    unittest.main()
