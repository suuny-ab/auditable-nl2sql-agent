# 当前开发状态

> 只保存当前事实；历史证据与回执见 [`docs/status-log/`](status-log/)，稳定边界见 [`PROJECT.md`](../PROJECT.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `in-progress` |
| 更新时间 | `2026-08-03` |
| 当前切片 | `HARDCASE-FIX-031`：修 6 条新增难题错例并唯一复跑冻结 40 题 |
| 最近完成 | `FROZEN-EVAL-40-030`：PR #24 合并为 `42e7edaa`，main 三个 CI job 全绿 |
| 当前状态 | 6 条最小修复与全部本地门禁通过；待冻结候选并消费唯一 40 题复跑 |
| 完成门 | 唯一复跑正确率 `>=32/40`，再推送 Draft PR、三路 CI 全绿后 squash 并复核 main |
| 项目基线 | `origin/main@42e7edaa25ae75c2479fe8555a602e1c93d8bf74`；main CI run `30755997930` 成功 |
| 阻碍 | 无；本单授权最多 40 次 Provider 调用、自动重试 `0`，推送与 Draft PR 已预授权 |

## 当前队列

- 基线轮次 `unseen40-20260802T155929Z` 固定为执行 `14/16`、正确 `32/40`、介入 `10/40`；
  37 条进入 transport，35 条保存 usage，共 `42410/3210/45620` prompt / completion / total tokens。
- 本单只修新增错例 `success-013..016` 与 `ambiguity-006..007`；前四条进入现有训练对知识层，后两条
  进入 Provider transport 前的确定性意图门。这 6 条均为已见开发集，不再声称未见。
- `success-010/011` 的旧题 transport 失败且无 usage，只记环境抖动，不修 transport、不补跑。
- 冻结题集不得修改：原始 SHA-256 `b3f698bc…1072ef`，完整规范化 SHA-256
  `c538bf96…97cef5`；工作流结构、Provider HTTP transport、安全边界和依赖不改。
- 新增 6 项逐错例定向测试全部通过；Python 全量 `95` 项测试、Web `2/2`、编译、44 包依赖、
  strict JSON、wheel、园丁、治理、Compose 与差异门全绿，真实 Provider 调用为 `0`。
- 评测只允许运行一次完整 40 题，最多 40 次真实 Provider 调用、自动重试 `0`；低于 `32/40`
  不推送，高于或持平才进入本单预授权的远端流程。

## 下一检查点

- 冻结实现候选提交；复制并核验封存题集、新业务库与新运行路径。
- 只消费本单唯一一轮 Provider 授权；运行开始后不补跑、不调参、不改题。
