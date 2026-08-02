"""Read-only checks for stale current-state claims in project documentation."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_PATHS = {"PROJECT.md", "docs/status.md"}
CURRENT_EXACT = {
    "AGENTS.md",
    "README.md",
    "deploy/README.md",
    "docs/work/README.md",
    "evals/README.md",
    "web/README.md",
}
CURRENT_PREFIXES = ("docs/engineering/",)
IGNORED_PARTS = {".git", ".local", ".venv", "node_modules"}
CURRENT_MARKER_RE = re.compile(r"当前|目前|现行|(?<!出)现在")
HISTORICAL_ANCHORS = (
    "历史",
    "当时",
    "首次",
    "本轮",
    "本片",
    "本单",
    "对应提交",
    "PR #",
    "回执",
    "已完成",
)
REVIEW_SAFE_CONTEXT = (
    "“当前 / 目前 / 现在 / 现行”",
    "当前态",
    "当前事实",
    "当前状态",
    "当前切片",
    "当前工作树",
    "当前节点",
)
MAIN_SHA_RE = re.compile(r"(?:origin/main|main)@`?([0-9a-f]{7,40})", re.IGNORECASE)
STATE_RE = re.compile(r"\bstate\s*[=:：]\s*`?([a-z0-9_-]+)", re.IGNORECASE)
SLICE_RE = re.compile(r"当前切片.*?`([A-Z][A-Z0-9-]*-\d{3})`")
TEST_COUNT_RE = re.compile(r"全量\s*`?(\d+)`?\s*项(?:本地\s*)?测试")


@dataclass(frozen=True)
class CanonicalFacts:
    project_state: str
    workflow_state: str
    current_slice: str
    main_sha: str
    full_test_count: int
    web_available: bool
    synthetic_data_only: bool
    provider_default_enabled: bool


@dataclass(frozen=True)
class Finding:
    level: str
    rule_id: str
    path: str
    line: int
    message: str


@dataclass(frozen=True)
class GardenerReport:
    canonical: CanonicalFacts
    scope: str
    scanned_files: int
    findings: tuple[Finding, ...]

    @property
    def stale_count(self) -> int:
        return sum(finding.level == "stale" for finding in self.findings)

    @property
    def review_count(self) -> int:
        return sum(finding.level == "review" for finding in self.findings)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _required_match(pattern: str, text: str, error: str, flags: int = 0) -> re.Match[str]:
    match = re.search(pattern, text, flags)
    if not match:
        raise ValueError(error)
    return match


def load_canonical_facts(root: Path) -> CanonicalFacts:
    project = _read(root / "PROJECT.md")
    status = _read(root / "docs/status.md")
    project_state = _required_match(
        r"> 状态：`([^`]+)`", project, "canonical_project_state_missing"
    ).group(1)
    workflow_state = _required_match(
        r"\| `state` \| `([^`]+)` \|", status, "canonical_workflow_state_missing"
    ).group(1)
    current_slice = _required_match(
        r"\| 当前切片 \| `([^`]+)`", status, "canonical_current_slice_missing"
    ).group(1)
    main_sha = _required_match(
        r"\| 项目基线 \| `origin/main@([0-9a-f]{7,40})`",
        status,
        "canonical_main_sha_missing",
        re.IGNORECASE,
    ).group(1).lower()
    full_test_count = int(
        _required_match(
            r"全量\s*`?(\d+)`?\s*项(?:本地\s*)?测试",
            status,
            "canonical_full_test_count_missing",
        ).group(1)
    )
    if "本地静态展示页已可运行" in project:
        web_available = True
    elif "网页和服务器部署仍待实现" in project:
        web_available = False
    else:
        raise ValueError("canonical_web_availability_missing")
    if "只用合成数据" not in project:
        raise ValueError("canonical_data_boundary_missing")
    if "Provider、费用、凭据、外部写入和公开发布默认不授权" not in project:
        raise ValueError("canonical_provider_default_missing")
    return CanonicalFacts(
        project_state=project_state,
        workflow_state=workflow_state,
        current_slice=current_slice,
        main_sha=main_sha,
        full_test_count=full_test_count,
        web_available=web_available,
        synthetic_data_only=True,
        provider_default_enabled=False,
    )


def markdown_paths(root: Path, scope: str) -> tuple[Path, ...]:
    paths: list[Path] = []
    for path in root.rglob("*.md"):
        if any(part in IGNORED_PARTS for part in path.relative_to(root).parts):
            continue
        relative = PurePosixPath(path.relative_to(root).as_posix()).as_posix()
        if (
            relative in CANONICAL_PATHS
            or relative.startswith("docs/status-log/")
            or (
                relative.startswith("docs/work/doc-gardener-")
                and "-report-" in relative
            )
        ):
            continue
        if scope == "current" and not (
            relative in CURRENT_EXACT or relative.startswith(CURRENT_PREFIXES)
        ):
            continue
        paths.append(path)
    return tuple(sorted(paths, key=lambda item: item.relative_to(root).as_posix()))


def _sha_matches(observed: str, canonical: str) -> bool:
    return observed.startswith(canonical) or canonical.startswith(observed)


def _has_current_marker(line: str) -> bool:
    return bool(CURRENT_MARKER_RE.search(line))


def _has_historical_anchor(line: str) -> bool:
    return any(marker in line for marker in HISTORICAL_ANCHORS) or bool(
        re.search(r"20\d{2}-\d{2}-\d{2}", line)
    )


def _line_findings(
    relative: str,
    line_number: int,
    line: str,
    facts: CanonicalFacts,
    scope: str,
) -> Iterable[Finding]:
    if not _has_current_marker(line):
        return
    historical = _has_historical_anchor(line)

    for match in MAIN_SHA_RE.finditer(line):
        observed = match.group(1).lower()
        if not historical and not _sha_matches(observed, facts.main_sha):
            yield Finding(
                "stale",
                "current_main_sha_conflict",
                relative,
                line_number,
                f"current main {observed} conflicts with canonical {facts.main_sha}",
            )

    for match in STATE_RE.finditer(line):
        observed = match.group(1)
        if not historical and observed not in {facts.project_state, facts.workflow_state}:
            yield Finding(
                "stale",
                "current_state_conflict",
                relative,
                line_number,
                f"current state {observed} is absent from canonical states",
            )

    for match in SLICE_RE.finditer(line):
        observed = match.group(1)
        if not historical and observed != facts.current_slice:
            yield Finding(
                "stale",
                "current_slice_conflict",
                relative,
                line_number,
                f"current slice {observed} conflicts with canonical {facts.current_slice}",
            )

    for match in TEST_COUNT_RE.finditer(line):
        observed = int(match.group(1))
        if not historical and observed != facts.full_test_count:
            yield Finding(
                "stale",
                "current_test_count_conflict",
                relative,
                line_number,
                f"current full test count {observed} conflicts with canonical {facts.full_test_count}",
            )

    current_web_available = re.search(
        r"(?:当前|目前|现在|现行).{0,24}网页.{0,16}(?:已实现|已上线|可运行|可用)|"
        r"网页.{0,24}(?:当前|目前|现在|现行).{0,16}(?:已实现|已上线|可运行|可用)",
        line,
    )
    if not historical and current_web_available and not facts.web_available:
        yield Finding(
            "stale",
            "current_web_availability_conflict",
            relative,
            line_number,
            "current runnable web claim conflicts with PROJECT.md",
        )

    current_web_unavailable = re.search(
        r"(?:当前|目前|现在|现行).{0,24}网页.{0,16}(?:没有可运行|尚未实现|仍待实现)|"
        r"网页.{0,24}(?:当前|目前|现在|现行).{0,16}(?:没有可运行|尚未实现|仍待实现)",
        line,
    )
    if not historical and current_web_unavailable and facts.web_available:
        yield Finding(
            "stale",
            "current_web_availability_conflict",
            relative,
            line_number,
            "current unavailable web claim conflicts with PROJECT.md",
        )

    current_real_data = re.search(
        r"(?:当前|目前|现在|现行).{0,24}(?:真实企业数据库|生产数据库|客户数据).{0,16}(?:已接入|已连接|使用)|"
        r"(?:真实企业数据库|生产数据库|客户数据).{0,24}(?:当前|目前|现在|现行).{0,16}(?:已接入|已连接|使用)",
        line,
    )
    if not historical and current_real_data and facts.synthetic_data_only:
        yield Finding(
            "stale",
            "current_data_boundary_conflict",
            relative,
            line_number,
            "current real-data claim conflicts with the synthetic-only boundary",
        )

    current_provider_default = re.search(
        r"(?:当前|目前|现在|现行).{0,24}Provider.{0,16}(?:默认启用|自动调用)|"
        r"Provider.{0,24}(?:当前|目前|现在|现行).{0,16}(?:默认启用|自动调用)",
        line,
        re.IGNORECASE,
    )
    if not historical and current_provider_default and not facts.provider_default_enabled:
        yield Finding(
            "stale",
            "current_provider_default_conflict",
            relative,
            line_number,
            "current Provider default-on claim conflicts with PROJECT.md",
        )

    if (
        scope == "all"
        and relative.startswith("docs/work/")
        and relative != "docs/work/README.md"
        and not _has_historical_anchor(line)
        and not any(marker in line for marker in REVIEW_SAFE_CONTEXT)
        and "docs/status.md" not in line
        and "PROJECT.md" not in line
    ):
        yield Finding(
            "review",
            "relative_current_in_historical_contract",
            relative,
            line_number,
            "historical work contract uses a relative current marker without a same-line time anchor",
        )


def scan(root: Path = ROOT, scope: str = "current") -> GardenerReport:
    if scope not in {"current", "all"}:
        raise ValueError(f"unsupported_scope:{scope}")
    facts = load_canonical_facts(root)
    paths = markdown_paths(root, scope)
    findings: list[Finding] = []
    for path in paths:
        relative = path.relative_to(root).as_posix()
        for line_number, line in enumerate(_read(path).splitlines(), start=1):
            findings.extend(_line_findings(relative, line_number, line, facts, scope))
    findings.sort(key=lambda item: (item.level, item.path, item.line, item.rule_id))
    return GardenerReport(facts, scope, len(paths), tuple(findings))


def render_markdown(report: GardenerReport) -> str:
    lines = [
        "# 文档园丁扫描",
        "",
        f"- scope: `{report.scope}`",
        f"- canonical project state: `{report.canonical.project_state}`",
        f"- canonical workflow state: `{report.canonical.workflow_state}`",
        f"- canonical current slice: `{report.canonical.current_slice}`",
        f"- canonical main: `{report.canonical.main_sha}`",
        f"- canonical full tests: `{report.canonical.full_test_count}`",
        f"- scanned files: `{report.scanned_files}`",
        f"- findings: stale `{report.stale_count}` / review `{report.review_count}`",
        "",
    ]
    if not report.findings:
        lines.append("没有发现确定腐坏或待人工判断项。")
    else:
        lines.extend(("| 级别 | 规则 | 位置 | 说明 |", "| --- | --- | --- | --- |"))
        for finding in report.findings:
            lines.append(
                f"| `{finding.level}` | `{finding.rule_id}` | "
                f"`{finding.path}:{finding.line}` | {finding.message} |"
            )
    return "\n".join(lines) + "\n"


def render_json(report: GardenerReport) -> str:
    payload = {
        "canonical": asdict(report.canonical),
        "scope": report.scope,
        "scanned_files": report.scanned_files,
        "summary": {"stale": report.stale_count, "review": report.review_count},
        "findings": [asdict(finding) for finding in report.findings],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--scope", choices=("current", "all"), default="current")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--fail-on", choices=("none", "stale", "review", "any"), default="none")
    args = parser.parse_args()
    try:
        report = scan(args.root.resolve(), args.scope)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"doc_gardener=failed error={exc}")
        return 2
    print(render_json(report) if args.format == "json" else render_markdown(report), end="")
    should_fail = (
        (args.fail_on == "stale" and report.stale_count > 0)
        or (args.fail_on == "review" and report.review_count > 0)
        or (args.fail_on == "any" and bool(report.findings))
    )
    if args.format == "markdown":
        print(
            f"doc_gardener=completed scope={report.scope} stale={report.stale_count} "
            f"review={report.review_count} fail_on={args.fail_on}"
        )
    return 1 if should_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
