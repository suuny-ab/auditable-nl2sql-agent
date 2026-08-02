from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from auditable_nl2sql import CANONICAL_QUESTION, WorkflowRunner
from auditable_nl2sql.demo import create_demo_database


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPLAY_PATH = PROJECT_ROOT / "web/app/data/container-demo-run.json"


class WebShowcaseReplayTests(unittest.TestCase):
    def test_static_replay_is_a_projection_of_the_real_fixture_run(self) -> None:
        replay = json.loads(REPLAY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(replay["schema_version"], "showcase-replay-v1")
        self.assertEqual(replay["source"]["data_class"], "synthetic_ecommerce")
        self.assertEqual(
            replay["source"]["public_read_url"],
            "https://47.84.34.86/nl2sql/api/v1/runs/container-demo-run",
        )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            business_database = create_demo_database(root / "business.sqlite3")
            with WorkflowRunner(
                business_database,
                root / "workflow.sqlite3",
            ) as runner:
                record = runner.run(
                    run_id="container-demo-run",
                    question=CANONICAL_QUESTION,
                )

        projected = replay["record"]
        for field in (
            "run_id",
            "question",
            "status",
            "provider_action",
            "generated_sql",
            "query_columns",
            "query_rows",
            "truncated",
            "result_row_limit",
            "result_validation",
            "answer",
            "attempt_count",
            "approval",
            "trajectory",
            "checkpoint_count",
        ):
            self.assertEqual(projected[field], record[field], field)
        self.assertEqual(
            projected["evidence"],
            {
                "schema_version": record["evidence"]["schema_version"],
                "fingerprint": record["evidence"]["fingerprint"],
            },
        )
        self.assertEqual(projected["attempt_count"], 1)
        self.assertIsNone(projected["approval"])
        self.assertEqual(len(projected["trajectory"]), 8)

    def test_page_has_no_interactive_query_or_provider_surface(self) -> None:
        page = (PROJECT_ROOT / "web/app/page.tsx").read_text(encoding="utf-8")
        forbidden = (
            "fetch(",
            "use client",
            "<form",
            "<input",
            "DEEPSEEK_API_KEY",
            "/api/v1/runs\"",
        )
        for marker in forbidden:
            self.assertNotIn(marker, page)

    def test_ci_builds_and_server_renders_the_showcase(self) -> None:
        workflow = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("  web:\n", workflow)
        self.assertIn("working-directory: web", workflow)
        self.assertIn("run: npm ci", workflow)
        self.assertIn("run: npm test", workflow)


if __name__ == "__main__":
    unittest.main()
