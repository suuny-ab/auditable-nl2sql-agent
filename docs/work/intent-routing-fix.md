# INTENT-ROUTING-FIX-026 切片合同

## Goal

为 `ambiguity-001/002` 与 `no_answer-001` 增加可审计、失败关闭的确定性意图门，在 Provider transport
前终止已知歧义或超出合成数据覆盖的问题，并用唯一一轮冻结评测验证正确率不低于 `17/20`。

## Non-goals

- 不修改 LangGraph 结构、审批门、只读执行、结果校验、evidence 或 answer 合同。
- 不修改训练对、正式模型、冻结评测集、判分口径或 Provider HTTP transport。
- 不增加新功能、依赖、向量库、真实数据、数据库值索引或代码层费用控制。
- 不自动重试、不补跑失败案例、不按结果调参刷分。

## Acceptance criteria

1. **WHEN** 问题只问通用销售额且没有时间、维度或排名范围，**THEN** 意图门返回 `clarify`，
   Provider 调用和 SQL 执行均为 `0`。
2. **WHEN** 问题问“最畅销商品”但未说明按销售额还是数量，**THEN** 意图门返回 `clarify`，
   Provider 调用和 SQL 执行均为 `0`。
3. **WHEN** 问题中的年份超出合成订单日期 `2026-01-05` 至 `2026-03-16`，**THEN** 意图门返回
   `no_answer`，Provider 调用和 SQL 执行均为 `0`。
4. **WHEN** 相邻成功问题带有 2026 年第一季度、销售渠道、客户、金额最高或明确数量等限定，
   **THEN** 意图门不拦截，仍调用原 Provider 一次。
5. **WHEN** 意图门命中，**THEN** trajectory 保存版本化规则 ID、最终 action、`provider_called=false`
   和无 usage 的脱敏回执，不伪造模型调用。
6. **WHEN** 完成实现，**THEN** 三条根因各有定向测试，Python 全量、Web、Compose、治理、园丁、
   编译、依赖与差异门全部通过。
7. **WHEN** 执行冻结评测，**THEN** 20 条案例只运行一轮，真实 Provider 调用不超过 20 次、自动
   重试 `0`、不补跑，并保存前后指标、真实调用数、usage 与安全哈希。
8. **WHEN** 新答案正确率不低于 `17/20`，**THEN** 按夜班预授权推送、创建 Draft PR，required CI
   全绿后 squash 合并；低于则不推送并如实战报。

## Rollback

回滚本切片提交即可删除意图策略和对应测试；它不迁移数据库、不改 checkpoint schema，也不改变
已合入的训练对。Git 忽略评测目录可单独删除，不影响产品状态。

## Rules restated

- 本轮 Provider 账户帽兜底，但只允许一轮、最多 20 次真实调用，自动重试 `0`；未用调用不得继承。
- 意图门只能减少 Provider 与 SQL 执行，不能把写操作、越权或审批请求放行。
- 三条错误和复跑升降均须如实记录；冻结集结果不能外推为生产可靠性或独立未见集能力。

## Root cause evidence

- `ambiguity-001`：销售额知识给出了默认计算公式，提示仅泛称“歧义时澄清”，没有强制时间 / 维度
  范围；上轮模型据此生成全时段销售额查询。
- `ambiguity-002`：schema 同时支持按成交金额和购买数量排名，问题没有指定“畅销”口径；当前上下文
  无绑定指标，上轮模型自行选择数量。
- `no_answer-001`：schema 只描述 `orders.order_date` 为日期文本，没有合成数据的实际覆盖区间；上轮
  模型生成 2027 Q1 查询，无法在 SQL 生成前判断事实不可用。

## Local evidence

- 新增 `intent-policy-v1`：年份超出 `2026-01-05` 至 `2026-03-16` 时返回 `no_answer`；通用销售额
  缺少范围、最畅销商品缺少金额 / 数量口径时返回 `clarify`。三个规则都在 Provider transport
  前运行。
- fake transport 对三条原误路由的调用次数均为 `0`；run record 分别形成
  `clarification_required / clarification_required / no_answer`，SQL 执行次数、approval、evidence
  与 answer 均为 `0/null`，业务库哈希不变。
- 意图回执明确保存 `provider=local-intent-policy`、`provider_called=false`、规则版本 / ID 和最终
  action，且没有 usage；不会把本地判断伪造成模型调用。
- 负向控制证明 2026 Q1、渠道、客户、销售额最高商品与明确销售数量等问题不被拦截；fixture 合同
  直接查询 `MIN/MAX(order_date)`，防止代码覆盖常量与合成数据漂移。
- Python `3.13.12` 定向 intent `5/5`、Provider `14/14`、全量 `81/81` 通过；`compileall` 与
  44 包依赖检查通过。所有测试进程均移除 Provider key，真实调用为 `0`。

## Evaluation result

- 唯一一轮 ID 为 `intentfix-20260802T142421Z`，报告创建于 `2026-08-02T14:25:05Z`；20 个
  case ID 唯一，自动重试 `0`，本轮结束后没有补跑。
- 同口径前后为：执行成功率 `8/8 → 8/8`，答案正确率 `17/20 → 20/20`，人工介入率
  `4/20 → 4/20`；错误案例 `3 → 0`，非成功类别 SQL 执行 `3 → 0`。
- 上轮 20 次 Provider 调用、prompt `22530`、completion `1849`、total `24379` tokens；本轮三条
  由本地意图门处理，真实调用 `17` 次，prompt `19367`、completion `1454`、total `20821` tokens。
- `ambiguity-001/002` 分别以 `revenue-scope-required / best-seller-metric-required` 进入
  `clarification_required`；`no_answer-001` 以 `synthetic-order-year-outside-coverage` 进入
  `no_answer`。三条均 `provider_called=false`、无 usage、SQL 执行 `0`。
- 3 条越权案例执行总数仍为 `0`；业务库整轮前后及逐案例均为
  `564572c5667de341521fcf0405b1749bd240b7a7318e02bf11b8938cce491ea7`。
- Git 忽略报告位于
  `.local/model-eval-runner/runs/intentfix-20260802T142421Z/report.json`，SHA-256 为
  `bb1f6f2fc6e6affe0edd2b9a66ceb387426d30e0233b9eb7177a4077e835f3fe`；未发现 key、
  Authorization、Bearer 或 GitHub token 标记。`20/20` 仍只是同一冻结合成集结果，不是未见集或
  生产可靠性证明。
