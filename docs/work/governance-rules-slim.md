# GOVERNANCE-RULES-SLIM-020 切片合同

## Goal

把仓库 `AGENTS.md` 收敛为不超过 110 行的启动 / 红线 / 指针索引，把执行细则迁入
`docs/engineering/`，并让授权默认值全文只有一个可机器验证的所有者。

## Non-goals

- 不改产品代码、产品依赖、数据、评测资产、Provider prompt、工作流或 API 合同。
- 不改 GitHub Actions 合同，不新增授权规则，不修改业务知识层。
- 不照抄 Traceable 的产品、部署、HOLDOUT、Reviewer 或多工作区治理；只复用索引与单一所有者模式。

## Acceptance criteria

1. **WHEN** 读取 `AGENTS.md`，**THEN** 总行数不超过 `110`，正文只包含启动顺序、事实 / 规则索引、
   项目硬红线和完成底线。
2. **WHEN** 跟随指针，**THEN** 心跳 / 派发 / 状态细则、开发 / 验证细则和授权 / Git 外部动作分别
   位于 `agent-workflow.md`、`development-flow.md`、`review.md`。
3. **WHEN** 扫描所有 tracked Markdown，**THEN** 授权正文 owner marker 与三个加粗档位标记只在
   `docs/engineering/review.md` 出现一次。
4. **WHEN** 运行 `python tools/check_governance.py`，**THEN** 行数、全部规则指针和唯一授权所有者
   断言通过；任一漂移都会非零退出。
5. **WHEN** 运行 Python 3.13 全量测试，**THEN** 治理合同测试和既有 59 项全部通过；`compileall`、
   依赖、diff 与范围检查通过。
6. **WHEN** 检查差异，**THEN** `api/src`、`evals`、`.github/workflows`、知识 JSON 和依赖文件均为零。
7. **WHEN** 精确远端 head 的 Python/container CI 全绿，**THEN** 按本单授权 squash 合并；否则不合并。

## Rollback

Revert 本切片提交即可恢复原规则入口并删除新增治理文档 / 检查；产品、数据和 CI 无迁移。

## Rules restated

- 只做治理规则索引与机器合同，不顺手改产品或增加规则。
- 授权默认值全文只在 `docs/engineering/review.md`；其他文件只提供指针。
- 本单只授权当前治理分支的一次 push、Draft PR 与精确 head 双 CI 绿后的 squash 合并，不部署。

## Reuse review

- 复用 Traceable PR #57 已验证的“入口只留启动 / 红线 / 索引、授权正文单一 owner、机器检查防
  回流”结构；该 PR head `bddb35b7` 的 governance/web/api/containers checks 全绿后已合并。
- NL2SQL 没有 Traceable 的产品文档体系、HOLDOUT、生产发布工具和独立 Reviewer 流程，因此只建
  3 份对应工程文档与 1 个轻量检查，不搬运其业务规则或大扫描器。

## Local evidence

- 从同步后的 `main@ff602261` 读取到原 `AGENTS.md` 已为 44 行，因此没有为了制造降幅删除必要
  红线；重构后为 43 行，只保留启动顺序、事实 / 规则索引、项目硬红线和完成底线。
- 心跳 / 派发 / 状态、开发 / 验证、授权 / Git 外部动作分别迁入 `agent-workflow.md`、
  `development-flow.md`、`review.md`；`docs/work/README.md` 明确历史合同不授予权限。
- `python tools/check_governance.py` 返回 `agents_lines=43`，全部 7 个指针存在；owner marker 和
  `默认通过 / 授权请求 / 红灯` 三个加粗档位在所有 tracked / untracked Markdown 中均只有
  `docs/engineering/review.md` 一个所有者。
- Python `3.13.12` 新增治理合同 1 项、全量 `60` 项测试通过；`compileall`、`uv pip check`、
  治理脚本和 `git diff --check` 通过。
- `api/src`、`evals`、`.github/workflows`、知识 JSON、依赖和容器合同差异均为 `0`；本片 Provider
  调用、token、费用、真实数据、部署与其他公开动作也均为 `0`。
