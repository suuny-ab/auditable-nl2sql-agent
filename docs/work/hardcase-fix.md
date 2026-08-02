# HARDCASE-FIX-031 切片合同

## Goal

把唯一 40 题基线中暴露的 6 条新增错例降格为开发集：用现有训练对知识层修复
`success-013..016`，用 Provider transport 前的确定性意图门修复 `ambiguity-006..007`；随后只复跑
一次冻结 40 题，与 `32/40` 基线如实比较。

## Non-goals

- 不修改评测题、reference SQL、expected、类别、判分逻辑或运行器。
- 不修改 LangGraph 工作流结构、审批门、只读执行、evidence、answer、API、网页或容器。
- 不修改 Provider HTTP transport、召回算法、阈值 `0.72`、最多 2 条的上限，也不增加依赖。
- 不修 `success-010/011` 的旧题 transport 失败，不补跑、不自动重试、不刷分。
- 不把已见开发集修复包装成独立未见集、泛化提升或生产可靠性证据。

## Acceptance criteria

1. **WHEN** 复核 `unseen40-20260802T155929Z`，**THEN** 6 条新增错例各有问题、失败边界、根因和
   最小修复记录；两条旧题 transport 失败单列为环境抖动，不进入修复范围。
2. **WHEN** 加载训练对，**THEN** 原 `success-001..012` 保持逐字不变，新增项只来自已暴露的
   `success-013..016`，且问题 / SQL 与冻结合同逐条相等。
3. **WHEN** 用四条成功开发集问题检索知识层，**THEN** 每题以相似度 `1.0` 首位召回自身 reference；
   SQL 都含 `LIMIT 5`，`013/014` 的别名与数值舍入合同保持精确。
4. **WHEN** 问题只说“折扣最大”却未说明金额或比例，或只泛问“复购情况”而未定义复购口径 / 指标，
   **THEN** 意图门返回 `clarify`，Provider 调用和 SQL 执行均为 `0`。
5. **WHEN** 相邻问题明确单件优惠金额、折扣率、复购率或“同月至少两笔”的复购定义，**THEN** 新规则
   不拦截，仍进入原 Provider 路径；写操作与其他失败关闭边界不放宽。
6. **WHEN** 完成本地实现，**THEN** 每条错例均有定向测试，Python 全量、编译、锁定依赖、strict
   JSON、wheel、园丁、治理、Web、Compose 与差异检查全部通过。
7. **WHEN** 开始真实评测，**THEN** 题集原始 SHA-256 仍为 `b3f698bc…1072ef`，业务库基线为
   `564572c5…1ea7`，新 checkpoint / report 路径预先不存在；40 题只运行一次，自动重试 `0`。
8. **WHEN** 评测结束，**THEN** 保存执行率、正确率、介入率、usage、六题前后、transport 抖动、越权 /
   非成功执行与业务库哈希；正确率不低于 `32/40` 才进入已授权远端流程，低于则不推送。
9. **WHEN** 达到发布门，**THEN** 推送精确 head、创建 Draft PR，api / web / container 三路 CI 全绿
   后 squash 合并并复核 main CI；随后只提交本地最终回执，不二次推送。

## Rollback

回滚本切片提交即可删除四条开发集训练对和两条意图规则；没有数据库迁移。Git 忽略的评测运行目录
可独立移除，不影响历史证据。

## Rules restated

- 本轮最多 40 次真实 Provider 调用、自动重试 `0`，冻结评测只允许完整运行一次；失败也不补跑。
- 只改知识层、意图门、定向测试和状态证据，不修改评测题或工作流结构；范围外事项停手写战报。
- SQL 仍须通过机械只读边界；越权与全部非成功类别 SQL 执行必须为 `0`，业务库哈希必须不变。

## Root-cause record

证据源为 `unseen40-20260802T155929Z/report.json`，SHA-256
`cba3eadc667f23b02754e5613283f7a5a6df7e2bac7634a57442fa21a403eec8`。

| case | 观察到的根因 | 最小修复 |
| --- | --- | --- |
| `success-013` | 查询方向和数据正确，但无 `LIMIT` 触发非预期审批；别名为 `max_discount_per_unit`，期望 `max_unit_discount` | 开发集训练对固定 reference 的有界 SQL、舍入和别名 |
| `success-014` | 无 `LIMIT` 触发非预期审批；销售额和平均每单未 `ROUND`，结果行不等于合同 | 开发集训练对固定 reference 的有界 SQL 与两处舍入 |
| `success-015` | 结果列 / 行正确，仅因无 `LIMIT` 触发非预期审批 | 开发集训练对固定 `LIMIT 5` |
| `success-016` | 窗口查询结果正确，仅因无 `LIMIT` 触发非预期审批 | 开发集训练对固定 `LIMIT 5` |
| `ambiguity-006` | “折扣最大”未说明金额还是比例、逐行还是聚合；模型把缺少显式折扣字段误判为无答案 | 有界意图规则要求明确折扣指标 |
| `ambiguity-007` | “复购情况”未定义复购次数 / 周期，也未指定客户数、复购率等指标；模型误判为无答案 | 有界意图规则要求明确复购定义或指标 |

`success-010/011` 是两条旧题 Provider transport 失败且没有 usage 的环境抖动；本单明确不修 transport，
不把它们当作产品错例，也不对它们补跑。

## Local evidence

- `training-pairs-v1` 的原 `success-001..012` 逐对象保持不变，只追加四条已见开发集 reference；严格
  加载器连续覆盖 16 条，并允许 reference 使用只读 `SELECT` 或 `WITH` CTE。文件 SHA-256 为
  `a2c5d2c6aa4c95f7e9caae332d504a86c0622e589d2118f2346a2cb9c529be79`。
- 四条新成功问题均以相似度 `1.0` 首位召回自身 reference，SQL 全含 `LIMIT 5`；`013` 固定
  `max_unit_discount`，`014` 固定 `revenue/avg_order_revenue` 的两位舍入，`016` 保留只读窗口 CTE。
- `intent-policy-v2` 新增 `discount-metric-required` 与 `repeat-purchase-definition-required`；两条原
  错例都在 Provider transport 前进入 `clarify`，相邻的单件优惠金额、折扣率、复购率和明确定义问题
  不被拦截。fake transport 和 SQL 执行为 `0`，业务库哈希不变。
- 新增逐错例定向 `6/6`、知识 / 意图 / Provider 定向 `40/40`、Python `3.13.12` 全量 `95/95`
  通过；测试进程移除 Provider key，真实 Provider 调用、usage、token 与费用均为 `0`。
- `compileall`、44 包依赖检查、四份知识 strict JSON、40 行 strict JSONL、园丁 current
  `9/0/0`、治理、Compose config、Web 构建 / SSR `2/2`、凭据模式与反向导入检查通过。
- wheel 成功包含四份知识 JSON；`evals/cases.jsonl` 与 `origin/main` 的 Git blob 完全相同，工作树
  CRLF 原始 SHA-256 为 `d12d1885…f3f28b0`，唯一运行将使用已封存 LF 字节
  `b3f698bc…1072ef`。工作流、Provider adapter、依赖与 Compose 均无差异。
- 实现与本地证据冻结为候选提交 `b8961614eeb99d047e3bcab355696d278e2e5513`；真实评测期间没有
  修改代码、知识数据、题面、gold、阈值、意图规则或 prompt。

## Single-run evaluation evidence

- 唯一轮次 `hardfix40-20260802T162815Z` 使用封存 LF 题集，SHA-256
  `b3f698bc49da2369f9c61739333c3815941954408caffc7b4d9ead4d781072ef`；40 个 case ID / 问题
  唯一，新业务库、checkpoint 与 report 路径在运行前均不存在。
- 40 个案例各运行一次，5 条由 `intent-policy-v2` 本地处理，35 条进入 Provider transport 且全部保存
  usage；自动重试 `0`，未补跑、未调参、未改题。执行 `14/16 → 16/16`、正确
  `32/40 → 40/40`、人工介入 `10/40 → 6/40`。
- 6 条开发集错例全部判对：`success-013..016` 直接完成并匹配列 / 行，`ambiguity-006..007` 以本地
  规则进入 `clarification_required`、SQL 执行 `0`。两条旧题 `success-010/011` 本轮 transport 正常，
  说明基线失败是环境抖动而非本片修复。
- 成功 / 歧义 / 无答案 / 越权 / 注入分别为 `16/16、7/7、7/7、5/5、5/5`；prompt /
  completion / total tokens 从 `42410/3210/45620` 变为 `43701/3243/46944`，usage receipt 均为
  `35` 条。本轮只证明对已见开发集错例的修复，不是新的泛化证据。
- 越权与全部非成功类别 SQL 执行均为 `0`；业务库运行前后和逐案例 SHA-256 始终为
  `564572c5667de341521fcf0405b1749bd240b7a7318e02bf11b8938cce491ea7`。
- Git 忽略报告 `.local/model-eval-runner/runs/hardfix40-20260802T162815Z/report.json` 的 SHA-256 为
  `72475050cb905b8aeb504c6406ed3a71edb35df0e2fa643620278db306c29758`，凭据 / Authorization /
  Bearer 模式扫描无命中。因 `40/40 >= 32/40`，满足进入本单预授权远端流程的门。

## Remote evidence

达到 `>=32/40` 发布门后填写；若未达到则记录未推送。
