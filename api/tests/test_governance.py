from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class GovernanceContractTests(unittest.TestCase):
    def test_rule_index_and_authorization_owner_are_unique(self) -> None:
        result = subprocess.run(
            [sys.executable, "tools/check_governance.py"],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("governance_check=passed", result.stdout)
        self.assertIn(
            "authorization_owner=docs/engineering/review.md",
            result.stdout,
        )
        self.assertIn("doc_gardener_stale=0", result.stdout)
        workflow = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("Run documentation current-state gate", workflow)
        self.assertIn(
            "python tools/doc_gardener.py --scope current --fail-on stale",
            workflow,
        )


if __name__ == "__main__":
    unittest.main()
