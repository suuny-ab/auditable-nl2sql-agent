"""Fail closed when the lightweight repository rule index drifts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENTS_PATH = ROOT / "AGENTS.md"
AUTHORIZATION_OWNER = "docs/engineering/review.md"
OWNER_MARKER = "## 授权默认值：唯一正文"
TIER_MARKERS = ("**默认通过**", "**授权请求**", "**红灯**")
REQUIRED_POINTERS = (
    "PROJECT.md",
    "docs/status.md",
    "docs/status-log/YYYY-MM.md",
    "docs/work/README.md",
    "docs/engineering/agent-workflow.md",
    "docs/engineering/development-flow.md",
    "docs/engineering/review.md",
)


def _tracked_markdown() -> list[str]:
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "*.md",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return sorted(
        item.decode("utf-8", "strict")
        for item in result.stdout.split(b"\0")
        if item
    )


def check_governance() -> list[str]:
    errors: list[str] = []
    agents = AGENTS_PATH.read_text(encoding="utf-8")
    agents_lines = len(agents.splitlines())
    if agents_lines > 110:
        errors.append(f"agents_line_limit_exceeded:{agents_lines}")
    for pointer in REQUIRED_POINTERS:
        if pointer not in agents:
            errors.append(f"agents_pointer_missing:{pointer}")

    documents = {
        path: (ROOT / path).read_text(encoding="utf-8")
        for path in _tracked_markdown()
    }
    owners = sorted(path for path, text in documents.items() if OWNER_MARKER in text)
    if owners != [AUTHORIZATION_OWNER]:
        errors.append(f"authorization_owner_invalid:{owners}")
    for marker in TIER_MARKERS:
        marker_owners = sorted(path for path, text in documents.items() if marker in text)
        if marker_owners != [AUTHORIZATION_OWNER]:
            errors.append(f"authorization_tier_owner_invalid:{marker}:{marker_owners}")
    gardener = subprocess.run(
        [
            sys.executable,
            "tools/doc_gardener.py",
            "--scope",
            "current",
            "--format",
            "json",
            "--fail-on",
            "stale",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if gardener.returncode != 0:
        detail = (gardener.stdout + gardener.stderr).strip().replace("\n", " ")
        errors.append(f"doc_gardener_gate_failed:{detail}")
    return errors


def main() -> int:
    errors = check_governance()
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        print(f"governance_check=failed errors={len(errors)}")
        return 1
    line_count = len(AGENTS_PATH.read_text(encoding="utf-8").splitlines())
    print(
        "governance_check=passed "
        f"agents_lines={line_count} authorization_owner={AUTHORIZATION_OWNER} "
        "doc_gardener_stale=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
