# 当前开发状态

> 只保存当前事实；历史证据与回执见 [`docs/status-log/`](status-log/)，稳定边界见 [`PROJECT.md`](../PROJECT.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `in-progress` |
| 更新时间 | `2026-08-03` |
| 当前切片 | `DATASOURCE-GOVERNANCE-039`：治理环境按数据源隔离 |
| 最近完成 | `METRICS-CARD-038`：PR #32 squash 为 `bbe0749`，main 三个 CI job 全绿 |
| 当前状态 | 两套 namespace、按源装载与跨源失败关闭已完成；本地全门绿，待远端评审 |
| 完成门 | 两套资源物理隔离、交叉绑定失败关闭、双库上下文指纹不变、全门绿后合并，不部署 |
| 项目基线 | `origin/main@bbe07495bc5bcf5c2a7949b027df84053fb6c66d`；main CI run `30763359201` 成功 |
| 阻碍 | 无；本片不调用 Provider、不运行冻结评测、不修改题目或部署 |

## 当前队列

- 主库现有术语 / 字段备注 / 枚举 / 16 条训练对迁入默认 namespace，不改资源内容。
- 第二库把 deterministic schema builder 的 13 个候选术语 / 16 条字段备注归入独立 namespace；
  枚举与训练对保持空集，不从业务行推断值。
- 生成器显式绑定 datasource；schema 不是该 namespace 的字段子集时在 transport 前失败关闭。
- 迁移前主 40 / 第二库 15 上下文 SHA-256 已冻结；本片只做离线等价回归，不运行真实评测。
- Python 全量 `125` 项测试（`3.13.12`，`125/125`）已通过；Provider 调用、评测与部署均为 `0`。

## 下一检查点

- 用夜班授权推送精确候选并创建 Draft PR；api / web / container 全绿后 squash 合并并复核 main。
- 合并后归档本单；不运行真实评测、不调用 Provider、不部署。
