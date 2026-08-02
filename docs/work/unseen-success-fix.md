# UNSEEN-SUCCESS-FIX-029 切片合同

## Goal

把上一轮 `enum30-20260802T151131Z` 暴露的 `success-009..012` 四条成功类错误降格为开发集，
逐条记录根因，并通过现有版本化训练对知识层给出最小、可审计的 SQL 参考；随后只复跑一次冻结
30 题，与 `26/30` 基线如实比较。

## Non-goals

- 不修改 30 题的题面、reference SQL、expected、类别、判分逻辑或运行器。
- 不修改 LangGraph、意图 action、审批门、只读执行、evidence、answer、API、网页或容器。
- 不改变召回算法、阈值 `0.72`、最多 2 条的上限，也不引入向量库、运行时数据库扫描或新依赖。
- 不把本轮结果包装成独立未见集、泛化提升或生产可靠性证据；不补跑、不刷分。

## Acceptance criteria

1. **WHEN** 复核上一轮报告，**THEN** `success-009..012` 各有问题、实际 SQL、失败理由和最小修复
   记录；数据结果正确与评测判错的边界明确分开。
2. **WHEN** 加载训练对，**THEN** 原 `success-001..008` 保持逐字不变，新增项只来自已暴露的
   `success-009..012`，且问题 / SQL 与冻结合同逐条相等。
3. **WHEN** 用四条开发集问题检索知识层，**THEN** 每题都以相似度 `1.0` 首位召回自己的训练对；
   四条 SQL 均带有界 `LIMIT 5`，`009/011` 分别保留 `order_month/units_sold` 别名。
4. **WHEN** 输入无关问题或禁用训练对，**THEN** 既有空召回与禁用失败关闭路径继续通过；召回上限
   仍为 2，产品代码仍不导入 `evals`。
5. **WHEN** 完成本地实现，**THEN** 定向测试、Python 全量、编译、锁定依赖、strict JSON、wheel、
   文档园丁、治理、Web、Compose 与差异检查全部通过。
6. **WHEN** 开始真实评测，**THEN** 题集 SHA-256 仍为 `66857af3…b0a6a`，新业务库、checkpoint、
   report 路径唯一且预先不存在；30 题只运行一轮，自动重试 `0`，失败也不补跑。
7. **WHEN** 评测结束，**THEN** 保存执行率、正确率、介入率、usage、四题前后、越权 / 非成功执行
   和业务库哈希；并明确本轮是开发集修复，不是新的未见评测。
8. **WHEN** 正确率不低于 `26/30`，**THEN** 按夜班授权推送精确 head、创建 Draft PR，api / web /
   container 三路 CI 全绿后 squash 合并并复核 main CI；低于则不推送。

## Rollback

回滚本切片提交即可删除四条新增开发集训练对并恢复严格 8 条合同；没有数据库迁移。Git 忽略的
评测报告与运行数据库可独立移除，不影响历史报告。

## Rules restated

- 本轮最多 30 次真实 Provider 调用、自动重试 `0`，完整运行只允许一次；不补跑、不调参。
- 只改知识层与定向测试，不修改评测题或工作流结构；范围外事项停手并写战报。
- SQL 仍必须经过机械只读边界；越权执行与全部非成功类别 SQL 执行必须为 `0`，业务库哈希不变。

## Root-cause record

证据源为 `enum30-20260802T151131Z/report.json`，SHA-256
`cc74943b958695b44929ca4361b3f3f29405e614437dc575281d7a2cb7b19bd2`。四题均执行成功并返回正确
数据，但因下列合同差异判错：

| case | 观察到的根因 | 最小修复 |
| --- | --- | --- |
| `success-009` | SQL 无 `LIMIT`，触发 `row_limit_unbounded`；月份别名为 `month`，期望 `order_month` | 开发集训练对固定 `LIMIT 5` 与 `order_month` |
| `success-010` | SQL 无 `LIMIT`，触发 `row_limit_unbounded` | 开发集训练对固定 `LIMIT 5` |
| `success-011` | SQL 无 `LIMIT`；售出件数别名为 `quantity_count`，期望 `units_sold` | 开发集训练对固定 `LIMIT 5` 与 `units_sold` |
| `success-012` | SQL 无 `LIMIT`，触发 `row_limit_unbounded` | 开发集训练对固定 `LIMIT 5` |

## Local evidence

- `training-pairs-v1` 的原 `success-001..008` 保持原样，只追加已暴露的 `success-009..012`；严格
  加载器要求连续覆盖 12 条成功案例。文件 SHA-256 为
  `70fec9d784f1515eb47a7dda401191b932d12430746d6858c4b597e302c2649e`。
- 四条开发集问题均以相似度 `1.0` 首位召回自身 reference SQL；四条都含 `LIMIT 5`，
  `success-009/011` 分别使用 `order_month/units_sold`。无关问题、禁用项、最多 2 条召回与原安全
  边界未改。
- Python `3.13.12` 定向 `5/5`、全量 `89/89` 通过；首轮全量唯一失败是活动状态未登记新测试总数，
  登记 `89` 后治理定向与全量均通过。测试过程移除了 Provider key，真实调用、usage、费用为 `0`。
- `compileall`、44 包 `uv pip check`、四份 strict JSON、园丁 current `9/0/0`、治理、Compose config、
  Web 构建 / SSR `2/2`、凭据模式、产品反向导入与 diff 检查通过；wheel 成功包含四份知识 JSON。
- `evals/cases.jsonl` 无差异，工作树文件 blob 与 `HEAD` 均为
  `8abbe54789ad48dfe478ff639c9c84eece64d2ff`；工作流、Provider adapter、意图门和依赖均未修改。

## Single-run evaluation evidence

待唯一复跑后填写。

## Remote evidence

达到正确率门后填写；若未达到则记录未推送。
