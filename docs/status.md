# 当前开发状态

> 只保存当前事实；历史证据与回执见 [`docs/status-log/`](status-log/)，稳定边界见 [`PROJECT.md`](../PROJECT.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `ready-to-push` |
| 更新时间 | `2026-08-02` |
| 当前切片 | `DOC-GARDENER-021`：NL2SQL 文档防腐扫描、当前态矛盾门禁与首次报告 |
| 最近完成 | `GOVERNANCE-RULES-SLIM-020`：PR #15 候选双 CI 绿后合并为 `4e9ec9de` |
| 当前状态 | 园丁活动扫描 `9/stale=0`、全扫 `29/stale=0/review=7`；全量 65 项测试与治理门已绿 |
| 完成门 | 本地范围 / 报告 / 门禁已通过；待精确 head `api` 与 `container` 双 CI 绿后 squash |
| 项目基线 | `origin/main@4e9ec9de`；PR 候选双绿，main API 绿而 container 因 Docker Hub 超时红 |
| 阻碍 | 无本地阻碍；不得把外部 registry 超时写成产品失败或 main CI 已绿 |

## 当前队列

- 进行中：用本单授权推送当前最终候选并创建 Draft PR，不追加园丁、产品或定时任务范围。
- 后续：本单合并后才重新评估最小网页；本片不自动开工网页。
- 保留：首次真实 20 条基线 `7/8`、`14/20`、`7/20`，不做 prompt 调优或补跑。

## 下一检查点

- 推送前复核园丁门、65 项测试、append-only 日志与禁改范围。
- 推送后核对远端精确 head，等待 `api` / `container` 双 CI，再按本单授权 squash。
