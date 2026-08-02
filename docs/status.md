# 当前开发状态

> 只保存当前事实；历史证据与回执见 [`docs/status-log/`](status-log/)，稳定边界见 [`PROJECT.md`](../PROJECT.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `in-progress` |
| 更新时间 | `2026-08-03` |
| 当前切片 | `SCHEMA-HOLDOUT-032`：第二合成 schema 的 15 题一次性泛化基线 |
| 最近完成 | `HARDCASE-FIX-031`：PR #25 合并为 `6372713a`，main 三个 CI job 全绿 |
| 当前状态 | 第二 fixture、15 题合同、gold 复算与全量门禁通过；待冻结候选并消费唯一 HOLDOUT |
| 完成门 | 首次 15 题泛化数字如实落盘、全量门禁通过，再完成 Draft PR、三路 CI 与 squash 合并 |
| 项目基线 | `origin/main@6372713ac69a54d8b8a112ea79f3e80176e1e6d9`；main CI run `30756883820` 成功 |
| 阻碍 | 无；本单授权最多 15 次 Provider 调用、自动重试 `0`，推送与 Draft PR 已预授权 |

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

## 下一检查点

- 提交并冻结实现候选，创建唯一新运行目录并复核 fixture / HOLDOUT 哈希、路径和调用上限。
- 只运行一次完整 15 题；结果无论高低都直接封存，不修改冻结资产或补跑。
