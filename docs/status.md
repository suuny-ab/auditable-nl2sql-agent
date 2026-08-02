# 当前开发状态

> 只保存当前事实；历史证据与回执见 [`docs/status-log/`](status-log/)，稳定边界见 [`PROJECT.md`](../PROJECT.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `in-review` |
| 更新时间 | `2026-08-03` |
| 当前切片 | `SCHEMA-HOLDOUT-032`：第二合成 schema 的 15 题一次性泛化基线 |
| 最近完成 | `HARDCASE-FIX-031`：PR #25 合并为 `6372713a`，main 三个 CI job 全绿 |
| 当前状态 | 首次换 schema 基线完成：执行 `0/7`、正确 `6/15`、介入 `2/15`；待远端回执 |
| 完成门 | 推送精确结果 head、Draft PR 三路 CI 全绿后 squash，并复核 main CI |
| 项目基线 | `origin/main@6372713ac69a54d8b8a112ea79f3e80176e1e6d9`；main CI run `30756883820` 成功 |
| 阻碍 | 无；唯一 Provider 授权已消费关闭，不补跑、不按低分调优；推送与 Draft PR 已预授权 |

## 当前队列

- 第二库固定为 `buyer_directory / merchandise / transaction_lines` 三表；订单头并入行事实，金额用
  INTEGER 分，状态 / 渠道改码，新旧表名和字段名零重合。
- 映射集固定 15 题、类别 `7/2/2/2/2`；问题 / expected 与主库同题相同，reference SQL 只按新
  schema 重写。主库同题对照为正确 `15/15`、成功执行 `7/7`、介入 `2/15`。
- HOLDOUT 在真实调用前冻结；首轮结果无论高低都是最终泛化基线，不修新库、不改题 / gold、
  不改知识 / 训练对 / prompt / 工作流，不补跑。
- 第二库 SHA-256 `ed9a2cda…78143d`；映射集原始 / 规范化 SHA-256 为
  `3a598167…7bb16 / 123c8317…779cd`，15 个 ID / 问题唯一，7 条成功 gold 离线复算全对。
- Python HOLDOUT 定向 `5/5`、Python 全量 `100` 项测试通过；Web `2/2`、编译、44 包依赖、strict JSONL、
  园丁、治理、Compose 与差异门全绿；知识、训练对、意图、Provider、工作流和主 40 题零差异。
- 唯一轮次 `schema15-20260802T165212Z`：主库同题 → 换 schema 为执行 `7/7 → 0/7`、正确
  `15/15 → 6/15`、介入 `2/15 → 2/15`；15 条 usage 的 tokens 为
  `19192/1541/20733 → 16434/999/17433`。
- 五类正确数为 `0/7、0/2、2/2、2/2、2/2`；7 条成功与 2 条歧义均保守判 `no_answer`，所有
  SQL 执行均为 `0`。业务库哈希不变，报告 SHA-256 `c3fe554c…ee15c8`，敏感模式无命中。
- 首次数字 `6/15` 已按 HOLDOUT 纪律封存；它直接暴露当前 schema 泛化不足，不修改资产、不补跑。

## 下一检查点

- 提交脱敏结果文档并按本单授权推送精确 head、创建 Draft PR。
- api / web / container 三路 CI 全绿后 squash 合并，再复核 main CI。
