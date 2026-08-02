# VALUE-COLLECTION-041：低基数字段有限取值采集

## Goal

在隔离治理环境中，以机械只读方式为合成 SQLite 数据源采集有限的低基数字段取值，重建第二
datasource 的枚举资源；运行时只加载版本化资源，并把与问题直接命中或 schema-derived 相关字段
命中的值注入 SQL 生成上下文。冻结候选后只执行一次第二库 15 题复测，与 `9/15、成功 1/7` 对比。

## Non-goals

- 不在 API / workflow 请求时扫描业务行，不接真实企业库或 AskTable 内部材料。
- 不生成自然语言别名，不实现人工标注 / 覆盖层，不修改题目、gold、判分器、审批门或 Provider action。
- 不针对单题调规则，不补跑、不刷分、不部署；本轮 Provider 最多 15 次，自动重试固定为 `0`。

## 采集边界

- 默认每字段最多 `16` 个不同值、候选字段最多 `32`、单值最多 `256` 字符、每字段超时 `2s`；硬上限
  分别为 `64 / 128 / 1024 / 10s`。参数非法或候选字段超限时失败关闭。
- 只候选 TEXT affinity 字段，并机械排除主键、外键以及标识符、展示名、日期时间、自由文本等高基数
  名称模式。查询最多取 `max_distinct_values + 1` 个非空不同值；出现第 `N+1` 个值、超长值或非文本
  值时整字段跳过，不把截断样本登记为完整枚举。
- SQL 标识符必须双引号转义；读取复用产品既有 `mode=ro + query_only + authorizer + timeout`，测试
  同时证明数据库 SHA-256 不变。`LIMIT` 只限制返回候选数，SQLite 仍可能为 DISTINCT 扫描更多行，
  因此超时是额外机械边界，不声称查询成本由 LIMIT 完全界定。
- SQLite 官方说明 SELECT 不修改数据库，DISTINCT 去重且 LIMIT 限制返回行数；参考
  <https://www.sqlite.org/lang_select.html>、<https://www.sqlite.org/limits.html>。

## 验收标准

1. **WHEN** 对合成 SQLite 库运行采集器，**THEN** 只读哈希前后不变，输出按表 / 字段 / 值稳定排序，
   并回执实际参数、候选数、采集数与跳过字段。
2. **WHEN** 字段是主外键、数值、展示名、日期 / 自由文本或包含第 `N+1` 个不同值，**THEN** 不进入
   枚举结果；高基数字段不返回前 N 个伪完整样本。
3. **WHEN** 表 / 字段含需转义的合法 SQLite 标识符，**THEN** 查询成功且不发生 SQL 注入；非法上限、
   过多候选或超长 / 非文本值失败关闭或整字段跳过。
4. **WHEN** 用默认上限重建第二库，**THEN** 只得到区域、客户分群、商品品类、状态、渠道 5 个字段
   的 17 个精确值，资源逐项等于采集器产物且 aliases 为空。
5. **WHEN** schema-derived 问题命中相关字段，**THEN** 该字段的有限值以稳定优先级进入
   `business_context.enum_values`，总数仍不超过 `8`；直接文字命中优先，值不得变成指令。
6. **WHEN** 运行主库 40 题上下文回归，**THEN** curated namespace 的旧指纹
   `29980F9A…7ABEE` 不变；跨 datasource 绑定仍在 transport 前失败关闭。
7. **WHEN** 运行产品链，**THEN** Provider / workflow 只读打包资源，不调用采集器、不新增运行时工具，
   产品代码仍不导入 `evals`。
8. **WHEN** 完成本地实现，**THEN** Python 全量、Web、编译、44 包依赖、strict JSON、园丁、治理、
   Compose、凭据 / 反向导入与完整容器门全绿，真实 Provider 调用仍为 `0`。
9. **WHEN** 候选冻结后开始唯一复测，**THEN** 新 business / checkpoint / report 路径预先不存在，
   15 个 case 各最多调用一次、自动重试 `0`；记录前后正确 / 成功 / 执行 / 介入、五类、usage、
   transport、安全计数、业务库与报告哈希，不补跑或据结果改候选。
10. **WHEN** 结果无论升降，**THEN** 按夜班授权推送精确 head、创建 Draft PR，web / api / container
    三路 CI 全绿后 squash 合并并复核 main；不部署。

## 回滚

revert 本切片 squash commit，恢复第二库空枚举资源、只按问题文字匹配枚举的上下文和无行值采集器；
Git 忽略评测数据库 / checkpoint / report 不做覆盖或迁移。

## 规则复述

- 只使用明确合成数据；采集器只在隔离治理构建中运行，API / workflow 不扫描业务行。
- 唯一第二库复测最多 15 次 Provider 调用、自动重试 `0`；不补跑、不调题、不刷分。
- 本单授权推送 / Draft PR 与 CI 绿后 squash；不授权部署、人工覆盖层或新的安全 / 费用边界。

## 基线

- `origin/main@896546f99f49a4de7376f30ca7c8e1443080128f`；隔离分支
  `agent/low-cardinality-value-index`，原工作区仍为 `codex/dispatch-receipt-rule@16cbf16` 且只有
  用户既有 `AGENTS.md` 修改。
- 最新第二库唯一轮次 `native15-20260802T203512Z`：正确 `9/15`、成功 `1/7`、执行 `7/7`、介入
  `7/15`，usage `27426 / 1642 / 29068`；报告 SHA-256 `4170ce38…6695a`。
- 当前第二库 `enum_values.json` 声明 3 张表但字段均为空；主库 curated 枚举已有 5 字段 17 值，
  运行时只在问题文字命中值 / 别名时注入。
