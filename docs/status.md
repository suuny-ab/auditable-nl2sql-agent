# 当前开发状态

> 只保存当前事实；历史证据与回执见 [`docs/status-log/`](status-log/)，稳定边界见 [`PROJECT.md`](../PROJECT.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `in-progress` |
| 更新时间 | `2026-08-03` |
| 当前切片 | `NATIVE-METADATA-040`：SQLite 原生注释爬取与分层合并 |
| 最近完成 | `DATASOURCE-GOVERNANCE-039`：PR #33 squash 为 `d122a05`，main 三个 CI job 全绿 |
| 当前状态 | 本地候选全门绿：Python 全量 `131` 项本地测试通过，注释爬取、三层合并与第二库 native 资源完成；真实 Provider 调用仍为 `0` |
| 完成门 | 注释只读爬取、native > generated 回退、双库离线回归与全门绿、唯一 15 题复测后合并 |
| 项目基线 | `origin/main@d122a0571bccbf7ca3901122a6bb9778b47b5ef7`；main CI run `30764979437` 成功 |
| 阻碍 | 无；待冻结候选后消费唯一 15 题 Provider 复测，自动重试 0，不补跑、不部署 |

## 当前队列

- SQLite 没有独立 comment 元数据列；本片只读取 `sqlite_schema.sql` 中与表 / 字段直接相邻的 DDL
  注释，不扫描业务行，不声称支持其他数据库方言。
- 第二库自动知识已在现有 datasource namespace 内重建；16 个字段均采用原生注释，合并器保留
  generated 与 empty 回退合同。
- 主库 40 题与第二库 15 题 / gold 不改；候选冻结前 Provider 调用为 `0`。
- 唯一复测与最新 `8/15` 对比，升降均封存；最多 15 次、重试 0，不补跑、不据结果调候选。

## 下一检查点

- 提交本地候选并记录精确冻结 SHA。
- 只执行唯一 15 题复测；如实落盘后进入夜班预授权远端流程，不部署。
