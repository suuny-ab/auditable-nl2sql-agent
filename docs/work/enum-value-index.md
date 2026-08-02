# ENUM-VALUE-INDEX-028 切片合同

## Goal

为 4 张合成业务表建立一份严格、版本化的低基数枚举值索引，把问题命中的业务词映射到已存在的
`table.field = value`，有界注入 SQL 生成上下文；随后只复跑一次冻结 30 题，并与 `26/30` 基线
如实比较。

## Non-goals

- 不修改冻结 30 题的题面、gold、类别、判分口径或原 8 条训练对。
- 不修改 LangGraph、审批门、只读执行、evidence、answer、API、网页、容器或数据库 schema。
- 不索引 ID、价格、数量等开放域 / 度量字段，不把当前 fixture 偶然出现的值伪装成封闭枚举。
- 不为抬分调题、调参、补跑、增加自动重试或实现向量库、数据库实时值扫描。

## Acceptance criteria

1. **WHEN** 加载枚举索引文件，**THEN** 文件覆盖 `customers/products/orders/order_items` 四张合成表，
   严格拒绝未知字段、重复表 / 字段 / 值 / 别名和非标准 JSON；`order_items` 明确没有可索引枚举。
2. **WHEN** 对照合成 fixture，**THEN** 只索引 `customers.region/segment`、`products.category`、
   `orders.status/sales_channel`，每个规范值与数据库 DISTINCT 值集合完全相等。
3. **WHEN** 问题包含规范值或别名，**THEN** `business-context-v3.enum_values` 只返回 schema 中存在的
   字段、规范数据库值和实际命中词，顺序稳定；未命中或字段不可用时为空。
4. **WHEN** 生成 Provider 请求，**THEN** 命中枚举值作为等值过滤提示注入，明确不能作为指令、
   不能用别名替代库内值、不能覆盖 schema / action / 安全规则。
5. **WHEN** 完成实现，**THEN** 定向命中、无命中、缺字段、fixture 值一致性和请求投影均有测试，
   Python 全量、编译、依赖、园丁、治理、Web、Compose、wheel、strict JSON 与差异门全部通过。
6. **WHEN** 开始真实评测，**THEN** 题集仍为 SHA-256 `66857af3…b0a6a`，新业务库、checkpoint、
   report 路径唯一且报告 / checkpoint 预先不存在；30 题只运行一轮、自动重试 `0`、不补跑。
7. **WHEN** 评测结束，**THEN** 保存与 `26/30` 的执行率、正确率、介入率、usage、错误案例、越权
   执行和业务库哈希对比；升降都如实记录，不倒写上一轮。
8. **WHEN** 正确率不低于 `26/30`，**THEN** 按夜班授权推送精确 head、创建 Draft PR，api / web /
   container 三路 CI 全绿后按常设档 squash 并复核 main CI；低于则不推送。

## Rollback

回滚本切片提交即可移除枚举文件、加载 / 匹配逻辑与上下文 v3；没有数据库迁移。Git 忽略的评测
报告与运行数据库可独立移除，不影响历史 `26/30` 基线。

## Rules restated

- 本轮最多 30 次真实 Provider 调用、自动重试 `0`，只允许完整运行一次；任何结果都不补跑。
- 枚举只来自明确合成 fixture，不能接真实数据或在运行时扫描用户数据库形成知识。
- SQL 仍受只读连接和机械授权边界约束；越权执行必须为 `0`，业务库哈希必须保持不变。

## Local evidence

- `enum-values-v1` 单文件声明 `customers/products/orders/order_items` 四张合成表；只索引
  `customers.region/segment`、`products.category`、`orders.status/sales_channel` 五个封闭字段的
  17 个规范值，`order_items.fields=[]`。文件 SHA-256 为
  `1db7eef4d8440cf4960e5ccd39d5a32fee908311c3db8ddb776e2d7b120c4245`。
- 严格加载器拒绝未知根字段、未知 schema 字段和重复别名；测试用现有只读执行器逐字段查询
  DISTINCT 值并与索引完全相等。规范值 / 别名全局唯一，最多注入 8 个匹配。
- `business-context-v3.enum_values` 对“华东地区已完成订单”稳定投影
  `customers.region=华东` 与 `orders.status=completed` 及实际命中词；移除 schema 字段后对应匹配
  消失，无关问题保持空列表。
- Provider fake transport 证明只把命中枚举作为规范值等值过滤提示；system prompt 明确别名不是
  库内值、元数据不是指令，不能覆盖 schema、action 或安全规则。工作流和只读边界未修改。
- Python `3.13.12` 全量 `85` 项测试通过；`compileall`、44 包依赖、strict JSON、含 4 份知识文件
  的 wheel、园丁 current `9/0/0`、治理、Compose config、Web 构建 / SSR `2/2` 均通过。
- 此阶段真实 Provider 调用、usage、token 与费用为 `0`；冻结 30 题、训练对和产品工作流均未修改。
- 实现与本地证据先冻结为提交 `ea279fe72e05cb01c9933a72e11e0740b29050bd`，评测期间没有修改代码、
  prompt、枚举数据、题面或 gold。

## Single-run evaluation evidence

- 首个零调用预检因 `git show --output` 对 blob 仍输出到 stdout 而得到空运行副本，严格数据合同在
  Provider 前拒绝；该目录没有 checkpoint / report。最终预检从上一轮基线运行副本恢复精确字节，
  去除换行差异后与当前 Git blob 完全相同，SHA-256 保持 `66857af3…b0a6a`。
- 唯一 Provider 轮次 `enum30-20260802T151131Z` 对 30 条各运行一次；3 条由本地意图门处理，真实
  Provider usage `27` 条，自动重试 `0`，未补跑、未调参、未改题。
- 基线 → 枚举索引：执行成功率 `12/12 → 12/12`、答案正确率 `26/30 → 26/30`、人工介入率
  `9/30 → 9/30`；没有案例改变正确性、action、初始状态、结果列或结果行。
- 仍错误的 4 条为 `success-009..012`：四条都因无有界 `LIMIT` 发生非预期审批，`009/011` 另有
  列别名不符；这些不属于枚举值根因，本轮不顺手修复。
- usage 从 prompt / completion / total `30577/2392/32969` 变为
  `32211/2262/34473` tokens，真实调用数仍为 `27`。正确率不降，但本轮没有证明指标提升。
- 4 条越权执行与全部非成功 SQL 执行均为 `0`；逐案例和整轮业务库 SHA-256 始终为
  `564572c5667de341521fcf0405b1749bd240b7a7318e02bf11b8938cce491ea7`。
- Git 忽略报告 `.local/model-eval-runner/runs/enum30-20260802T151131Z/report.json` 的 SHA-256 为
  `cc74943b958695b44929ca4361b3f3f29405e614437dc575281d7a2cb7b19bd2`，敏感标记扫描无命中。
  因 `26/30 >= 26/30`，满足进入本单预授权远端流程的门。

## Remote evidence

达到正确率门后填写；若未达到则记录未推送。
