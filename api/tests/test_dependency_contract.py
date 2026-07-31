from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


API_ROOT = Path(__file__).resolve().parents[1]


class DependencyContractTests(unittest.TestCase):
    def test_pyproject_direct_dependencies_match_requirements_input_and_lock(self) -> None:
        pyproject = tomllib.loads((API_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        project_dependencies = set(pyproject["project"]["dependencies"])
        requirements = {
            line.strip()
            for line in (API_ROOT / "requirements-base.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }

        self.assertEqual(project_dependencies, requirements)
        lock_lines = (API_ROOT / "requirements-base.lock").read_text(
            encoding="utf-8"
        ).splitlines()
        for requirement in sorted(requirements):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement + " \\", lock_lines)


if __name__ == "__main__":
    unittest.main()
