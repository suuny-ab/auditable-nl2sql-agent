# STATUS-TWO-LAYERS-017 切片合同

## Goal

把单文件状态账拆为小型当前层与按月 append-only 历史层，使当前事实可在 30 行内读完，同时完整
保留迁移前的状态与验证回执。

## Non-goals

- 不改 `api/src`、`api/tests`、`evals`、依赖或 CI 合同。
- 不改评测结果、产品能力、安全边界或部署状态。
- 不改规则族其他文件；`AGENTS.md` 只改状态事实源的两层指针。
- 不部署，不调用 Provider，不发布镜像，不接触真实数据。

## Acceptance criteria

1. **WHEN** 读取 `docs/status.md`，**THEN** 文件不超过 30 行，且只含顶部字段表、当前队列和
   下一检查点。
2. **WHEN** 读取 `docs/status-log/2026-08.md`，**THEN** 能逐字恢复迁移前
   `origin/main@e391aad7:docs/status.md` 的 326 行规范化文本。
3. **WHEN** 后续记录历史证据，**THEN** 只能在对应月度日志末尾追加，不修改或回写既有条目。
4. **WHEN** 读取项目 `AGENTS.md`，**THEN** 当前事实与历史事实的两层来源均有明确指针，其他规则
   文本不变。
5. **WHEN** 写本轮战报，**THEN** 新的带时间戳三行记录位于文件顶部，原有记录全部保留在其后。
6. **WHEN** 运行 Python 3.13 全量测试，**THEN** 当前 55 项基线全部通过。
7. **WHEN** 检查改动边界，**THEN** 产品、评测和 CI 文件差异均为零。
8. **WHEN** Draft PR 的远端 CI 运行，**THEN** `api` 与 `container` 两个 job 都成功后才允许
   squash 合并。

## Rollback

本切片只调整文档结构；revert 合并提交即可恢复迁移前的单文件状态账。

## Rules restated

- 当前事实只写 `docs/status.md`；历史证据和回执只追加到 `docs/status-log/YYYY-MM.md`。
- 初始迁移必须用来源 SHA、行数和内容比较证明历史零丢失。
- 本切片只使用合成数据且 Provider 调用为零；服务器部署属于后续红灯动作。

## Frozen migration baseline

- 来源：`origin/main@e391aad7226691724cd52e265748e0d4e335d292:docs/status.md`
- 行数：`326`
- Windows 工作树文件 SHA-256：`7f33f3fcb8b9e80fee8a25e0910afd44a97e4dd63980a82f0179bcb738d2f11a`
- 当前真实基线：PR #12 已 squash 合并为 `e391aad7`，main CI run `30740065993` 的
  `api`/`container` 双 job 成功；服务器部署未开工。

## Local evidence

- 规范化文本比较：日志快照与 `git show origin/main:docs/status.md` 完全相同，均为 326 行。
- 新 `docs/status.md` 为 25 行，只含字段表、当前队列和下一检查点。
- `AGENTS.md` 只把单层状态指针改成当前层/月度历史层两条；产品、评测和 CI 差异为零。
- Python `3.13.12` 全量 55 项测试通过；`compileall`、`pip check`、`git diff --check` 通过。
- Provider 调用、凭据读取、token 消耗、费用、部署和真实数据接触均为 `0`。
