# 当前开发状态

> 只保存当前事实；历史证据与回执见 [`docs/status-log/`](status-log/)，稳定边界见 [`PROJECT.md`](../PROJECT.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `in-review` |
| 更新时间 | `2026-08-02` |
| 当前切片 | `UNSEEN-SUCCESS-FIX-029`：四条已暴露成功题的开发集修复与唯一 30 题复跑 |
| 最近完成 | `ENUM-VALUE-INDEX-028`：PR #22 合并为 `57e462f9`，main 三个 CI job 全绿 |
| 当前状态 | 唯一复跑完成：执行 `12/12`、正确 `30/30`、介入 `5/30`，达到不降门，待远端回执 |
| 完成门 | 推送精确结果 head、Draft PR 三个 CI job 全绿后 squash，并复核 main CI |
| 项目基线 | `origin/main@57e462f9829fc81dd8445378bb07b0433a541441` |
| 阻碍 | 无；本轮 Provider 授权已消费关闭，不再调用或补跑；推送与 Draft PR 已预授权 |

## 当前队列

- 上轮四条错误 `success-009..012` 都得到正确数据，但均因 SQL 缺有界 `LIMIT` 触发非预期审批；
  `009/011` 另有 `order_month/units_sold` 别名差异。
- 四题从本轮起明确作为已见开发集；已新增与冻结 reference SQL 相等的版本化训练对，不修改题本、
  召回算法、工作流或安全边界。
- 唯一轮次 `devfix30-20260802T153713Z`：执行 `12/12 → 12/12`、正确 `26/30 → 30/30`、介入
  `9/30 → 5/30`；四条开发集错误全部转正。
- 真实 usage `27` 条，prompt / completion / total 为 `32774/2276/35050`；自动重试 `0`，越权与
  全部非成功 SQL 执行 `0`，业务库哈希不变。
- 新增知识层 5 条定向与全量 89 项测试通过；Web `2/2`、编译、44 包依赖、strict JSON、园丁、
  治理、Compose、wheel 与差异门全绿。

## 下一检查点

- 提交脱敏结果文档；不再运行 Provider、评测器或修改知识层。
- 按本单授权推送并创建 Draft PR；api / web / container 全绿后 squash，再复核 main CI。
