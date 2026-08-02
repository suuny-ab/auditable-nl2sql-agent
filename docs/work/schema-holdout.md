# SCHEMA-HOLDOUT-032 切片合同

## Goal

建立第二套确定性合成业务库，用与主库相同的 15 个业务问题、不同的 schema 与重写后的 reference SQL
运行一次泛化基线；首个数字按 HOLDOUT 纪律封存，并与主库同题 `15/15` 结果如实对比。

## Non-goals

- 不修改产品知识层、16 条训练对、意图门、Provider prompt、LangGraph 工作流或安全边界。
- 不修改现有冻结 40 题、主库 fixture、判分口径或既有报告。
- 不依据泛化分数调整新库、映射题、gold、schema、训练对、prompt 或代码；不补跑、不刷分。
- 不接真实企业数据，不新增依赖，不把一次合成 HOLDOUT 外推为生产可靠性。

## Acceptance criteria

1. **WHEN** 创建第二业务库，**THEN** 它固定为 `buyer_directory / merchandise / transaction_lines`
   三表；订单头并入行事实表、金额使用整数分、状态 / 渠道使用新编码，表名和字段名与主库零重合。
2. **WHEN** 重建第二业务库，**THEN** schema、行数、业务语义和 SHA-256 均确定；已有目标拒绝覆盖，
   失败创建不留下半成品。
3. **WHEN** 加载 HOLDOUT，**THEN** 精确包含 15 个主库来源 ID，类别固定 `7/2/2/2/2`，问题、类别、
   expected 与冻结 40 题逐条相同，成功与旧越权 gold 使用新表重写且不引用旧表名。
4. **WHEN** 用新 reference SQL 离线复算，**THEN** 7 条成功的列 / 行 / 排序与主库同题 expected 相等；
   2 条越权仍失败关闭，业务库前后哈希不变，非成功 SQL 执行为 `0`。
5. **WHEN** 运行模型评测器，**THEN** 它由显式 `schema-holdout-v1` 合同验证 15 题；默认参数仍只接受
   原 40 题合同，报告、审批模拟、usage 和安全统计格式不变。
6. **WHEN** 完成本地实现，**THEN** 新增定向测试、Python 全量、编译、锁定依赖、strict JSONL、
   园丁、治理、Web、Compose 与差异检查全绿；知识、训练对、意图、工作流、Provider adapter 零差异。
7. **WHEN** 冻结候选，**THEN** 记录代码 head、新库 SHA-256、HOLDOUT 原始 / 规范化 SHA-256、15 个
   ID 与问题唯一性；新 checkpoint / report 路径预先不存在，凭据只确认存在而不打印。
8. **WHEN** 启动真实基线，**THEN** 15 题完整运行恰好一次，真实 Provider 调用不超过 15 次，自动
   重试 `0`；任何分数或 transport 失败都不补跑、不调参、不改冻结资产。
9. **WHEN** 基线结束，**THEN** 保存执行率、正确率、介入率、usage、逐类结果、主库同题对比、越权 /
   非成功执行、业务库哈希和脱敏报告哈希；首次数字即为最终泛化基线。
10. **WHEN** 本地合同与唯一基线完成，**THEN** 按夜班授权推送精确 head、建 Draft PR，api / web /
    container 全绿后 squash 合并并复核 main CI；最终归档回执不二次推送。

## Rollback

回滚本切片提交即可删除第二 fixture、独立 HOLDOUT 合同、映射集、评测器显式合同选择与对应测试；
没有生产数据库迁移。Git 忽略的运行数据库、checkpoint 和报告可独立移除。

## Rules restated

- HOLDOUT 的 schema、数据、题目和 gold 在任何真实 Provider 调用前冻结；第一次完整数字无论高低都封存。
- 本轮最多 15 次真实 Provider 调用、自动重试 `0`、完整运行一次；失败也不补跑。
- 不改知识层、训练对、产品工作流或安全边界；越权与全部非成功 SQL 执行必须为 `0`，业务库哈希不变。

## Frozen design

- 新 schema：`buyer_directory(buyer_key, buyer_label, market_area, buyer_class)`、
  `merchandise(sku, title, department, catalog_price_cents)`、
  `transaction_lines(ticket_no, buyer_key, sku, occurred_on, state_code, source_code, units, paid_unit_cents)`。
- 结构差异：主库 4 表拆分订单头 / 明细，新库 3 表并入行事实；REAL 元改为 INTEGER 分；
  `paid/shipped/completed/cancelled` 改为 `SETTLED/IN_TRANSIT/CLOSED/VOID`，渠道改为
  `WEB/SHOP/PLATFORM`。数据仍为明确标注的同语义合成 fixture。
- 选题固定为 `success-001/004/005/006/007/013/016`、`ambiguity-003/004`、
  `no_answer-002/003`、`unauthorized-001/005`、`injection-001/005`，类别 `7/2/2/2/2`；顺序固定。
- 主库同题对照来自唯一轮次 `hardfix40-20260802T162815Z`（报告 SHA-256
  `72475050cb905b8aeb504c6406ed3a71edb35df0e2fa643620278db306c29758`）：15 题正确
  `15/15`、成功执行 `7/7`、介入 `2/15`。该对照只用于比较，不参与新库调优。

## Local evidence

- `evals.schema_holdout` 可重复生成同字节 SQLite，拒绝覆盖已有目标；三表列集合与冻结设计逐项相等，
  且与主库 4 个表名、14 个字段名零交集。合成行数为买方 `4`、商品 `5`、交易行 `11`、唯一订单
  `6`；数据库 SHA-256 为 `ed9a2cda873588525d5637f6708209348d62b63d31c265cc1471c5acdc78143d`。
- `schema_holdout_cases.jsonl` 精确 15 题，原始 SHA-256
  `3a598167cb62fec7bfc5598543df6c82868ddf85865e55f95303966428d7bb16`、规范化 SHA-256
  `123c8317e93d49f9253adecd33697cea6bfefba522e037dfa0331ce4676779cd`；15 个 ID / 问题唯一，
  类别 `7/2/2/2/2`，问题 / expected 与来源 40 题相等。
- 8 条有 reference 的映射全部使用新表且与主库 gold 不同；7 条成功经现有只读工作流复算得到主库
  同题列 / 行，2 条越权失败关闭，业务库哈希不变。主 40 题 blob 与规范化哈希
  `c538bf96…97cef5` 均未改变。
- 评测器默认仍只接受原 40 题；只有显式 `schema-holdout-v1` 才接受 15 题，报告、审批模拟、usage、
  自动重试 `0` 与安全统计代码复用原实现，没有另写宽松判分器。
- Python `3.13.12` HOLDOUT 定向 `5/5`、相关合同 / 运行器 `10/10`、全量 `100/100` 通过；Web
  构建 / SSR `2/2`、编译、44 包依赖、两份 strict JSONL、园丁 current `9/0/0`、治理、Compose、
  凭据模式和 diff 检查全绿。
- 一次重验中 100 项产品测试已执行，仅治理子测因活动状态写作“100/100”而无法提取总数；未改代码或
  冻结资产，只改为机器合同要求的“全量 100 项测试通过”，随后全量 `100/100` 与治理均通过。
- 产品知识、16 条训练对、意图、Provider adapter、工作流、主库、现有 40 题、依赖和 Compose 相对
  `origin/main` 零差异。本阶段测试进程移除 Provider key，真实调用、usage、token 与费用为 `0`。

## Single-run HOLDOUT evidence

首次完整运行后填写；开始后不得修改冻结资产或补跑。

## Remote evidence

远端流程完成后填写。
