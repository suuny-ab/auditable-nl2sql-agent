# PARAPHRASE-EVAL-034 切片合同

## Goal

从主库 40 题中按五类各选 2 题，为每题冻结 3 种含义不变、措辞差异明显的自然问法，并仅运行一次
最多 30 次真实 Provider 的改述基线；把改述正确率、相对原题的稳定率与掉分清单如实落盘。

## Non-goals

- 不修改主 40 题、reference SQL、expected、判分口径或已封存原题结果。
- 不针对改述掉分题调优；不改知识层、训练对、意图门、Provider prompt / adapter 或工作流。
- 不补跑、不刷分，不把本次合成改述结果外推为生产自然语言泛化能力。
- 不接真实数据库，不新增依赖、API、网页、容器或部署能力。

## Acceptance criteria

1. **WHEN** 加载改述题集，**THEN** 来源恰好 10 题且五类各 2 题；每个来源题恰好映射 3 个唯一问题，
   改述总数为 30。
2. **WHEN** 审查每个来源组，**THEN** 三题分别标为 `formal / colloquial / restructured`，逐条保存
   `meaning_preserved=true`，并且不与原题逐字重复。
3. **WHEN** 物化改述案例，**THEN** 类别、reference SQL 和 expected 与来源题完全一致；主 40 题
   LF 规范化 SHA-256 保持 `dca2a3a0…c6a794`。
4. **WHEN** 读取来源基线，**THEN** 只使用已封存轮次 `unseen40-20260802T155929Z` 与报告
   SHA-256 `cba3eadc…03eec8`；本次选中原题正确率固定为 `8/10`。
5. **WHEN** 运行离线合同，**THEN** 30 个 case ID / 问题唯一、每类 6 题，成功与旧越权 reference
   均由现有只读工作流复算，错误映射或来源漂移失败关闭。
6. **WHEN** 完成本地实现，**THEN** Python 全量、编译、依赖、strict JSON、园丁、治理、Web、
   Compose、凭据与反向导入检查全绿；真实 Provider 调用仍为 `0`。
7. **WHEN** 候选提交冻结后启动真实评测，**THEN** 新业务库、checkpoint、report 路径预先不存在；
   30 个变体最多各调用 Provider 一次、自动重试 `0`，任何分数或 transport 结果都不补跑。
8. **WHEN** 唯一评测结束，**THEN** 保存变体正确率、与原题结果一致的稳定率、完整稳定来源数、
   掉分 / 改善清单、usage、越权 / 非成功执行、业务库与报告哈希。
9. **WHEN** 本地结果落盘，**THEN** 按夜班授权推送精确 head、创建 Draft PR；api / web / container
   三路 CI 全绿后 squash 合并并复核 main CI。

## Rollback

Revert 本切片提交即可移除改述数据、严格合同、运行器合同选项和文档；主 40 题与产品代码没有迁移。
Git 忽略的唯一运行报告、业务库与 checkpoint 可独立保留或删除，不影响主评测历史。

## Rules restated

- 真实 Provider 调用最多 30 次、自动重试 `0`，完整运行只允许一次；不补跑、不调优、不刷分。
- 改述只改措辞，来源题的业务含义、范围、操作与 expected 不得变化；主 40 题保持字节身份。
- SQL 继续受机械只读边界；越权执行必须为 `0`，业务库逐案例和整轮哈希必须不变。

## Selection and rewrite design

| 来源题 | 原题正确 | 选择理由 | 三种改写轴 |
| --- | --- | --- | --- |
| `success-001` | 是 | 基础时间范围聚合 | 日期展开 / 口语 Q1 / 口径前置 |
| `success-013` | 否 | 多表、价格口径、排序 | 正式列项 / 口语差价 / 排序前置 |
| `ambiguity-001` | 是 | 缺时间与范围 | 正式 / 口语 / 目标前置 |
| `ambiguity-006` | 否 | 优惠额与折扣率仍未定义 | 正式 / 口语 / 条件前置 |
| `no_answer-001` | 是 | 超出数据日期覆盖 | 月份展开 / 口语 / 时间前置 |
| `no_answer-006` | 是 | schema 缺优惠券事实 | 逐笔正式 / 口语 / 对象前置 |
| `unauthorized-001` | 是 | 直接删除 | 状态码 / 口语清理 / 操作前置 |
| `unauthorized-005` | 是 | 分析包装写操作 | 更新前置 / 口语 / 写回前置 |
| `injection-001` | 是 | 直接提示注入加 DDL | 正式 / 口语 / 优先级伪装 |
| `injection-005` | 是 | 客户备注间接注入 | SYSTEM 伪装 / 留言伪装 / 管理员伪装 |

## Local evidence

- 严格物化得到 10 个来源、30 个唯一 case ID 与问题，五类各 6 题；每个来源恰好包含
  `formal / colloquial / restructured`，并逐条保存 `meaning_preserved=true`。
- 来源题类别、reference SQL 和 expected 逐项相等；主 40 题 LF SHA-256 为
  `dca2a3a01f33975d17c9636d5e8e5ab0df3144394ac7d96e5342e21cd4c6a794`。成功与旧越权 reference
  由现有只读工作流复算，业务库不变；漂移与缺少含义声明均由合同拒绝。
- 改述定向 `4/4`，Python `3.13.12` 全量 110 项测试通过；Web 生产构建 / SSR `2/2`、编译、
  44 条锁依赖、两份 strict JSONL 与改述 strict JSON、园丁 current `9/0/0`、治理、Compose config、
  差异、凭据模式和产品反向导入检查全绿。
- 完整 Compose 本地验收确认进程身份 `10001:10001`、health `read_only=true`、固定 run 完成、
  POST 创建为 `405`，业务库与 checkpoint 哈希前后相等；验收后容器已删除，临时 LF 入口恢复原字节。
- 本片相对 `origin/main` 只增加改述数据 / 合同 / 测试 / 文档并给评测器增加显式合同 loader；主 40 题、
  产品代码、知识、训练对、意图、Provider、工作流、依赖、Web 与 Compose 均无差异。真实 Provider
  调用、usage、token 与费用为 `0`。

## Single-run evaluation evidence

待唯一一轮真实评测完成后填写。

## Remote evidence

待远端流程完成后填写。
