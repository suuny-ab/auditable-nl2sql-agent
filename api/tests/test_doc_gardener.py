from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.doc_gardener import render_json, render_markdown, scan


PROJECT = """# 项目事实

> 状态：`mvp_development`

- 只用合成数据，不接真实企业数据库或公司内部材料。
- Provider、费用、凭据、外部写入和公开发布默认不授权。

网页和服务器部署仍待实现。
"""

PROJECT_WITH_WEB = PROJECT.replace(
    "网页和服务器部署仍待实现。",
    "本地静态展示页已可运行，页面尚未部署。",
)

STATUS = """# 当前开发状态

| `state` | `in-progress` |
| 当前切片 | `DOC-GARDENER-021`：文档园丁 |
| 当前状态 | 全量 60 项测试已绿 |
| 项目基线 | `origin/main@aaaaaaaa`；远端事实 |
"""


class DocGardenerTests(unittest.TestCase):
    def build_root(self, files: dict[str, str]) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        base = {"PROJECT.md": PROJECT, "docs/status.md": STATUS, **files}
        for relative, content in base.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return root

    def test_current_claims_conflicting_with_canonical_facts_are_stale(self) -> None:
        root = self.build_root(
            {
                "README.md": (
                    "当前项目基线是 `origin/main@bbbbbbb`。\n"
                    "当前 state=ready，当前切片是 `OLD-SLICE-001`。\n"
                    "当前全量 59 项测试已绿。\n"
                    "当前网页已上线且可运行。\n"
                    "当前生产数据库已接入使用。\n"
                    "当前 Provider 默认启用。\n"
                )
            }
        )

        report = scan(root)

        self.assertEqual(report.stale_count, 7)
        self.assertEqual(
            {finding.rule_id for finding in report.findings},
            {
                "current_data_boundary_conflict",
                "current_main_sha_conflict",
                "current_provider_default_conflict",
                "current_slice_conflict",
                "current_state_conflict",
                "current_test_count_conflict",
                "current_web_availability_conflict",
            },
        )

    def test_matching_current_claims_and_unavailable_web_are_clean(self) -> None:
        root = self.build_root(
            {
                "README.md": (
                    "当前项目基线是 `origin/main@aaaaaaaa`。\n"
                    "当前 state=in-progress，当前切片是 `DOC-GARDENER-021`。\n"
                    "当前全量 60 项测试已绿。\n"
                    "2026-08-01 当时当前项目基线是 `origin/main@bbbbbbb`。\n"
                ),
                "web/README.md": "当前没有可运行网页。\n",
            }
        )

        report = scan(root)

        self.assertEqual(report.stale_count, 0)
        self.assertEqual(report.review_count, 0)

    def test_available_web_canonical_rejects_current_unavailable_claim(self) -> None:
        root = self.build_root(
            {
                "PROJECT.md": PROJECT_WITH_WEB,
                "web/README.md": "当前网页仍待实现，没有可运行版本。\n",
            }
        )

        report = scan(root)

        self.assertEqual(report.stale_count, 1)
        self.assertEqual(report.findings[0].rule_id, "current_web_availability_conflict")

    def test_manual_all_scope_lists_unanchored_historical_current_for_review(self) -> None:
        root = self.build_root(
            {
                "README.md": "当前事实见状态。\n",
                "docs/work/old-slice.md": (
                    "当前边界仍是只读。\n"
                    "本轮当前边界已由 2026-08-01 的测试证明。\n"
                    "精确版本同时出现在两个依赖文件中。\n"
                ),
                "docs/work/doc-gardener-initial-report-20260802.md": (
                    "当前网页已上线。\n"
                ),
                "docs/work/doc-gardener-initial-report-20260802.md": (
                    "当前网页已上线。\n"
                ),
            }
        )

        current = scan(root, "current")
        full = scan(root, "all")

        self.assertEqual(current.review_count, 0)
        self.assertEqual(full.scanned_files, 2)
        self.assertEqual(full.review_count, 1)
        self.assertEqual(full.stale_count, 0)
        self.assertEqual(full.findings[0].rule_id, "relative_current_in_historical_contract")

    def test_reports_are_deterministic_and_json_is_structured(self) -> None:
        root = self.build_root({"README.md": "当前网页已上线。\n"})
        report = scan(root)

        self.assertEqual(render_markdown(report), render_markdown(scan(root)))
        payload = json.loads(render_json(report))
        self.assertEqual(payload["summary"], {"review": 0, "stale": 1})
        self.assertEqual(payload["scope"], "current")

    def test_stale_cli_gate_fails_closed(self) -> None:
        root = self.build_root({"README.md": "当前网页已上线。\n"})
        script = Path(__file__).resolve().parents[2] / "tools/doc_gardener.py"

        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--root",
                str(root),
                "--scope",
                "current",
                "--format",
                "json",
                "--fail-on",
                "stale",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["summary"]["stale"], 1)


if __name__ == "__main__":
    unittest.main()
