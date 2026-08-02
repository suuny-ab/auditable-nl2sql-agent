# 公开数字口径卡

> 事实快照：`main@e7686bbae6e2ebff6d0be0510a7802d1dae2fba7`（2026-08-03）
>
> 用法：面试或评审中出现下列数字时，先看“定义 / 测量方法”，再看“边界”。历史单次结果不会因
> 后续复跑被倒写；报告与 PR 只证明对应合成数据、代码版本和测量合同。

## 先统一三个词

- **答案正确率**：所有案例中，Provider action、最终状态、审批边界和预期结果全部命中的比例；
  成功题还要逐项比较结果列、结果行和截断状态。
- **执行成功率**：只在预期为 `success` 的案例中，最终完成、恰好执行一次且无执行错误的比例；
  SQL 能执行不等于答案正确。
- **人工介入率**：首次运行进入 `pending_approval` 的案例占全部案例的比例；评测随后模拟决定，
  不改变这一计数。三项定义见[评测器报告](work/model-eval-runner.md)与
  [PR #9](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/9)。

## 1. 调优曲线：五个公开里程碑

| 数字 | 定义与测量方法 | 数据集 | 单次 / 可复跑 | 边界：不是什么 | 证据 |
| --- | --- | --- | --- | --- | --- |
| `14/20` | 首次真实固定基线的答案正确数；按上面的严格正确合同逐题判定 | 原始 20 题冻结合成开发集 | 历史单次已封存；合同可复算，新运行不得倒写旧值 | 不是生产准确率，也不是未见泛化 | [报告](work/model-eval-runner.md) · [PR #9](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/9) |
| `17/20` | 加入版本化训练对召回后，同口径逐题判定的答案正确数 | 与 `14/20` 完全相同的 20 题 | 唯一真实复跑；自动重试 `0` | 不是独立测试集提升 | [报告](work/training-pair-frozen-eval.md) · [PR #19](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/19) |
| `20/20` | 在观察前三条残余后加入本地意图门，再按同一合同判定 | 与前两步相同的 20 题 | 唯一真实复跑；自动重试 `0` | 是已见开发集满分，不是泛化满分 | [报告](work/intent-routing-fix.md) · [PR #20](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/20) |
| `30/30` | 扩充到 30 题后，观察四条成功题错误并修复，再逐题判定 | 已观察错误的 30 题主库开发集 | 唯一修复后复跑；自动重试 `0` | 不是新的 30 题未见基线；未见基线原为 `26/30` | [报告](work/unseen-success-fix.md) · [PR #23](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/23) |
| `40/40` | 40 题基线暴露错误后做定向修复，再按五类合同逐题判定 | 已观察错误的 40 题主库开发集 | 唯一修复后复跑；自动重试 `0` | 不是未见 schema、真实业务或生产可靠性证明 | [报告](work/hardcase-fix.md) · [PR #25](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/25) |

读图结论只有一个：`14/20 → 17/20 → 20/20 → 30/30 → 40/40` 是开发过程弧线，不能解释成
五次独立未见评测。页面口径合同见[验证弧线报告](work/showcase-validation-arc.md)与
[PR #31](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/31)。

## 2. 泛化三维与换库短板

| 数字 | 定义与测量方法 | 数据集 | 单次 / 可复跑 | 边界：不是什么 | 证据 |
| --- | --- | --- | --- | --- | --- |
| `40/40` | 主库五类案例全部满足严格答案合同 | 已见 40 题主库开发集 | 历史单次修复后结果 | 作为主库参照，不充当未见泛化 | [报告](work/hardcase-fix.md) · [PR #25](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/25) |
| `8/15；成功 0/7` | 紧凑结构摘要轮的总正确与成功类正确数 | 表/字段零重合、状态与渠道改码、金额用整数分的第二合成库 15 题 | 历史唯一摘要轮；自动重试 `0` | 是后续改道的历史参照，不再是最新结果；摘要本身没有提分 | [报告](work/schema-summary-injection.md) · [PR #30](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/30) |
| `9/15；成功 1/7` | SQLite DDL 原生注释进入 schema-derived 上下文后的严格判定 | 与上一行完全相同的第二库 15 题 | 原生注释候选的唯一复跑；自动重试 `0` | 是同一换库开发集上的局部改善，不是新 unseen schema 证据 | [报告](work/native-metadata.md) · [PR #34](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/34) |
| `9/15；成功 1/7` | 再加入 5 个低基数字段的 17 个值后的严格判定 | 与前两行相同的第二库 15 题 | 有限字段值候选的唯一复跑；自动重试 `0` | 指标持平只证明没有退化，不能宣称值采集带来提升 | [报告](work/low-cardinality-value-collection.md) · [PR #35](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/35) |
| 投影 `27/30` | 旧完整改述正确数 `24/30`，加上已见掉分三题定向回归的 `+3` | 旧 30 条改述基线 + 仅三条定向复测 | 只重跑三条；未重跑完整 30 条 | 不是新的完整正确率，更不是新稳定率 | [报告](work/paraphrase-synonym-coverage.md) · [PR #29](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/29) |

三个分母和观测条件不同，不能平均、相减或拼成一个“综合泛化分”。尤其是 `40/40` 与最新成功题
`1/7` 同时成立：前者是已见主库开发集，后者是同一换 schema 开发复测暴露的剩余短板。

## 3. 改述正确率与稳定率

| 数字 | 定义与测量方法 | 数据集 | 单次 / 可复跑 | 边界：不是什么 | 证据 |
| --- | --- | --- | --- | --- | --- |
| `24/30` | 30 条改述中满足原题 action、状态、审批与结果合同的数量 | 主库五类各选 2 个来源，每个来源 3 种含义不变改述 | 唯一完整改述基线 | 是改述正确率，不自动等于逐题稳定 | [报告](work/paraphrase-eval.md) · [PR #28](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/28) |
| `24/30 = 80%` | 每条改述的“正确/错误”是否与对应来源原题一致；一致即稳定 | 同一 10 个来源、30 条改述 | 唯一完整基线 | 稳定错误也计“稳定”；不同题的掉分与改善会互相抵消 | [报告](work/paraphrase-eval.md) · [PR #28](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/28) |
| `8/10 = 80%` | 一个来源的三种改述全部与该来源原题判定一致，才算“完整稳定来源” | 同一 10 个来源组 | 唯一完整基线 | 与逐变体 `80%` 数值相同是巧合，不代表逐题行为相同 | [报告](work/paraphrase-eval.md) · [PR #28](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/28) |
| `0/3 → 3/3` | 只对已知掉分的三种“无范围销售额”改述做定向回归 | `ambiguity-001-p1..p3` | 唯一三题复测；实际 Provider 调用 `0` | 只证明已见回归修好，不能生成新的全量稳定率 | [报告](work/paraphrase-synonym-coverage.md) · [PR #29](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/29) |

截至本快照，没有“修复后完整 30 题稳定率”。因此只能公开旧完整稳定率 `80%` 和正确率投影
`27/30`，不能宣称稳定率已变为 `90%`。

## 4. 预算与有界队列参数

### 4.1 评测调用预算

| 数字 | 定义与测量方法 | 数据集 / 任务 | 单次 / 可复跑 | 边界：不是什么 | 证据 |
| --- | --- | --- | --- | --- | --- |
| 最多 `20` 次、重试 `0` | 每题至多进入 Provider 一次 | 原始 20 题冻结轮次 | 每次授权只允许一个完整轮次 | 不是账户额度，也不能继承到补跑 | [报告](work/model-eval-runner.md) · [PR #9](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/9) |
| 最多 `30` 次、重试 `0` | 30 个案例/改述各至多一次 | 30 题主库或 30 条改述 | 每个对应切片只允许一个完整轮次 | 两个“30”不是同一数据集或共享预算 | [主库报告](work/frozen-eval-30.md) · [PR #21](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/21)；[改述报告](work/paraphrase-eval.md) · [PR #28](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/28) |
| 最多 `40` 次、重试 `0` | 40 个主库案例各至多一次 | 五类 40 题轮次 | 一个完整轮次 | 不是长期调用配额 | [报告](work/frozen-eval-40.md) · [PR #24](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/24) |
| 最多 `15` 次、重试 `0` | 第二库 15 题各至多一次 | 换 schema HOLDOUT / 各授权复测 | 每个授权切片一个完整轮次 | 不能把未用调用结转或用来刷分 | [摘要轮](work/schema-summary-injection.md) · [PR #30](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/30)；[原生注释轮](work/native-metadata.md) · [PR #34](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/34)；[有限值轮](work/low-cardinality-value-collection.md) · [PR #35](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/35) |
| 最多 `3` 次、重试 `0` | 三条已知改述掉分各至多进入 Provider 一次；本轮被本地意图门全部截停 | 定向三题回归 | 只运行一次 | 上限为 `3` 不等于实际调用；实际调用是 `0` | [报告](work/paraphrase-synonym-coverage.md) · [PR #29](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/29) |

仓库没有人民币/美元金额预算数字；代码层不实现账户预算，费用帽和告警留在 Provider 账户层。
因此不能从上述“最多调用次数”推导金额承诺。

### 4.2 有界候选与执行参数

| 数字 | 定义与测量方法 | 作用对象 | 可复跑性 | 边界：不是什么 | 证据 |
| --- | --- | --- | --- | --- | --- |
| 阈值 `0.72`、最多 `2` 条 | 规范化字符二元组 Jaccard 达阈值后，按分数与 case ID 稳定排序并截取 | 训练对候选上下文 | 确定性合同，可离线复算 | 不是向量检索、概率置信度或模型准确率 | [报告](work/training-pair-retrieval.md) · [PR #18](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/18) |
| 最多 `8` 个 | 问题直接命中值优先，schema-derived 相关字段值随后按稳定顺序截断 | 合成枚举过滤提示 | 确定性合同，可离线复算 | 不是数据库运行时扫描，也不是每题必有 8 个命中 | [主库枚举](work/enum-value-index.md) · [PR #22](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/22)；[第二库有限值](work/low-cardinality-value-collection.md) · [PR #35](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/35) |
| 默认 `16 值 / 32 字段 / 256 字符 / 2s` | 第二库离线治理采集器的每字段值数、候选字段、单值长度与每字段超时；硬上限为 `64 / 128 / 1024 / 10s` | 仅隔离合成治理环境 | 确定性只读构建，可离线复算 | 不在 API 请求时扫描行，也不把前 N 个值冒充完整枚举 | [报告](work/low-cardinality-value-collection.md) · [PR #35](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/35) |
| 审批阈值 `5` 行 | 明确 `LIMIT` 超过 5 或多行上限不明时先挂起；单行聚合和不超过阈值的简单 `LIMIT` 可直行 | SQL 审批门 | 产品合同，可重复验证 | 不是写权限；批准仍不能越过机械只读边界 | [报告](work/approval-gate.md) · [PR #2](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/2) |
| 结果硬上限 `100` 行 | run 创建时把上限写入 state；执行最多取该上限并用额外一行判断截断 | 只读结果集 | 产品合同，可跨进程回查 | 不是“所有查询都会返回 100 行”；截断结果会失败关闭 | [报告](work/result-evidence.md) · [PR #3](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/3) |

这里的“队列”指有界候选/上下文与审批入口；项目没有实现异步任务队列、并发 worker 吞吐或 SLA，
不得把 `2`、`8`、`5`、`100` 解释成并发量或性能指标。

## 5. 数据集与测试规模

| 数字 | 定义与测量方法 | 范围 | 单次 / 可复跑 | 边界：不是什么 | 证据 |
| --- | --- | --- | --- | --- | --- |
| `40` 题，分类 `16/7/7/5/5` | 严格 JSONL 合同统计 success / ambiguity / no-answer / unauthorized / injection | 当前主评测集 | 合同可离线重放；真实 Provider 轮次需新授权 | 题量不是生产覆盖率 | [报告](work/frozen-eval-40.md) · [PR #24](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/24) |
| 第二库 `15` 题 | 从主库选择 15 个同题，映射到表字段零重合的第二合成 schema | 换 schema HOLDOUT | 合同可离线重放；每个真实轮次单次 | 不是 15 个独立业务域 | [报告](work/schema-holdout.md) · [PR #26](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/26) |
| 改述 `10 × 3 = 30` 条 | 五类各选 2 个来源，每题 formal / colloquial / restructured 三种改述 | 改述评测集 | 合同可离线物化；真实基线只跑一次 | 三种模板不代表自然语言全分布 | [报告](work/paraphrase-eval.md) · [PR #28](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/28) |
| Python `136/136` | `unittest discover` 在锁定依赖环境运行的全部产品与合同测试 | `api/tests` | 每个提交可重复运行 | 测试通过不等于模型正确率或生产可靠性 | [报告](work/low-cardinality-value-collection.md) · [PR #35](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/35) |
| Web `3/3` | 生产构建后对 SSR 页面、验证弧线证据和无交互边界运行 Node 合同 | `web/tests` | 每个提交可重复运行 | 不是浏览器矩阵、可用性研究或部署验收 | [报告](work/showcase-validation-arc.md) · [PR #31](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/31) |
| CI `3` 路 | GitHub Actions 分别运行 api / web / container job | PR 与 main | 每次 push 重新运行 | 三路绿不证明 v2 已部署 | [工作流](../.github/workflows/ci.yml) · [PR #35](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/35) |

## 复述时的最短安全版本

> 主库已见开发集从 `14/20` 调到 `40/40`；换 schema 从结构摘要历史轮 `8/15、成功 0/7` 经原生
> 注释到最新 `9/15、成功 1/7`，有限字段值采集未新增提升；完整
> 改述基线的正确率与稳定率都是 `24/30`，三题修复后只有正确率投影 `27/30`，没有新的完整稳定率。
> 所有真实评测均单轮、自动重试 `0`，测试规模是 Python `136/136`、Web `3/3`；这些都只针对
> 合成数据和对应版本，不是生产可靠性或部署证明。
