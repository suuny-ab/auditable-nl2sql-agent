# PARAPHRASE-SYNONYM-COVERAGE-035 切片合同

## Goal

修复同义改述基线中 `ambiguity-001-p1..p3` 的无范围销售额漏判：只扩展通用业务同义词与既有规则
的句式覆盖，不增加单题分支；对冻结三题运行唯一一次最多 3 次 Provider 的定向复测，并把
`24/30` 前后变化如实落盘。

## Non-goals

- 不修改 30 条改述问题、来源映射、reference SQL、expected、判分口径或基线报告。
- 不改训练对、枚举、字段备注、Provider prompt / transport、工作流、审批或机械只读边界。
- 不针对三道题写 case ID、整句或结果分支；不重跑其余 27 题，不补跑、不刷分。
- 不接真实数据库，不新增依赖、API、网页、容器或部署能力。

## Acceptance criteria

1. **WHEN** 复核基线 trajectory，**THEN** 记录三题均绕过 `revenue-scope-required`；p1 / p3 已命中
   “收入 / 销售额”但通用请求包装残留，p2 的“卖了多少钱”没有业务术语命中。
2. **WHEN** 应用修复，**THEN** 只在“销售额”知识条目新增通用同义表达，并扩展既有无范围销售额
   规则的词项 / 填充词；判断分支、action、reason 与 rule ID 不变。
3. **WHEN** 输入三条冻结掉分题与“成交额 / 销售总额”等邻近改写，**THEN** 全部确定性返回
   `clarify + revenue-scope-required`；业务上下文能按新增别名命中“销售额”。
4. **WHEN** 输入主库 16 条成功题与 4 条带时间、分组或明确全量范围的同义问题，**THEN** 全部继续
   Provider 路由，不被新增覆盖误拦。
5. **WHEN** 读取定向复测合同，**THEN** 只从原 `paraphrase_cases.json` 选择
   `ambiguity-001-p1..p3`，问题 / expected / 含义不变声明保持冻结，拒绝任何替换。
6. **WHEN** 完成本地实现，**THEN** 主库定向、Python 全量、编译、依赖、strict JSON、园丁、治理、
   Web、Compose、凭据与反向导入检查全绿，真实 Provider 调用仍为 `0`。
7. **WHEN** 候选冻结后开始复测，**THEN** 新 business / checkpoint / report 路径预先不存在；三题
   最多各进入 Provider 一次、自动重试 `0`，首次完整结果无论升降都封存。
8. **WHEN** 复测完成，**THEN** 保存三题 `0/3` 前后、投影完整改述 `24/30` 前后、usage、Provider
   调用数、非成功 / 越权执行、数据库与报告哈希。
9. **WHEN** 结果落盘，**THEN** 按夜班授权推送精确 head、创建 Draft PR；api / web / container
   三路 CI 全绿后 squash 合并并复核 main CI。

## Rollback

Revert 本切片提交即可删除新增别名、句式填充词、定向复测合同与文档；30 条改述题和产品数据没有
迁移。Git 忽略的唯一报告、业务库与 checkpoint 可独立保留，不影响旧基线。

## Rules restated

- 唯一复测最多 3 次 Provider 调用、自动重试 `0`；不补跑、不调题、不刷分。
- 只扩通用词项覆盖，不增加 case ID、整句或结果专用逻辑；主库全部成功题不得被误拦。
- SQL 继续受机械只读边界；越权与三条歧义的执行必须为 `0`，业务库哈希必须不变。

## Root-cause evidence

- 基线三题都得到 `query` 并执行：p1 / p3 的 Provider reason 已把问题解释为 total revenue，p2 也
  自行推断为 revenue；三题均未被本地 `revenue-scope-required` 截断。
- p1 “请给出销售收入总额”已通过旧别名“收入”命中业务术语，但 `_is_unscoped_revenue_question`
  去除收入后仍残留“请给出销售总额”；p3 去除“销售额 / 查询”后仍残留“我想”。
- p2 “一共卖了多少钱”既不命中旧的销售额词项，也缺少“一共”包装覆盖。因此根因是同一通用词法
  覆盖边界的两面，不是 schema、SQL、训练对或 Provider transport 故障。

## Local evidence

- 红灯测试先证明三条冻结掉分题与“成交额 / 销售总额”两个邻近表达均返回 `None`；业务上下文只在
  p1 以旧别名“收入”命中，另外三个新增别名均缺失。主库全部 16 条成功题在红灯阶段仍正常路由。
- “销售额”知识条目只新增 `销售收入 / 销售总额 / 成交额 / 卖了多少钱`；既有意图规则只增加相同
  词项与 `请 / 给出 / 我想 / 知道 / 一共 / 总额` 填充词，函数分支、action、reason 与 rule ID
  没有变化；行为合同版本升为 `intent-policy-v3`。修复后全部红灯题与邻近题转绿。
- 业务知识 / 意图 / 改述子合同 / 比较器 / 运行器定向 `36/36`；主库 16 条成功题和 4 条带范围的
  邻近同义问题全部继续 Provider 路由。Python `3.13.12` 全量 115 项测试通过。
- 零 success 的三题子集将执行成功率记录为 `0/0, value=null`，而非失败；集成测试用拒绝网络的
  transport 证明三题均由本地意图门终止、transport 调用 `0`、非成功执行 `0`。
- Web 生产构建 / SSR `2/2`、编译、44 条锁依赖、两份 strict JSONL、改述 / 业务术语 strict JSON、
  园丁 current `9/0/0`、治理、Compose config、凭据模式、产品反向导入与差异门全绿。
- 完整 Compose 本地验收确认进程 `10001:10001`、health `read_only=true`、固定 run 完成、POST 创建
  为 `405`，业务库与 checkpoint 哈希前后相等；验收后容器删除，临时 LF 入口恢复原字节。
- 本片未修改主 40 题、30 条改述题、HOLDOUT、训练对、Provider、工作流、依赖、Web 或 Compose；
  真实 Provider 调用、usage、token 与费用为 `0`。

## Single-run evaluation evidence

- 冻结候选为 `74a99644b417ae88ec4f381321c825f30c120c04`；唯一轮次
  `revenuepara3-20260802T181238Z` 的 business / checkpoint / report / 题集副本路径预先不存在，
  只选择 `ambiguity-001-p1..p3`，自动重试 `0`，没有补跑、换题或调优。
- 三题 workflow 各执行一次后均形成 `clarification_required + revenue-scope-required` checkpoint，
  attempt count 均为 `0`，本地 policy receipt 均为 `provider_called=false`；真实 Provider 调用、usage、
  prompt / completion / total token 均为 `0`。
- 所选三题正确率 `0/3 → 3/3`，投影完整 30 题 `24/30 → 27/30`（`+3`）；非成功 SQL 执行
  `3 → 0`，本轮越权和非成功执行均为 `0`，执行成功率因无 success 类案例记为 `0/0, value=null`。
- 旧汇总器在三条 checkpoint 全部写完后因零分母退出；遵守不补跑边界，没有再次调用 `run()`，仅用
  `WorkflowRunReader` 读取既有三条终态并经同一判分 / usage / metric 写出标准报告。该边界已有拒绝
  网络的集成回归测试。
- 业务库前后及当前 SHA-256 均为 `564572c5667de341521fcf0405b1749bd240b7a7318e02bf11b8938cce491ea7`；
  报告 SHA-256 为 `18801b7b7f0a4b3f6d50da63738ca348c87d1701d95116a9f0e3d0c70e6b491e`，
  敏感模式命中 `0`。

## Remote evidence

待远端流程完成后填写。
