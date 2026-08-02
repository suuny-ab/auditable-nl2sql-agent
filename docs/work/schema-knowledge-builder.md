# SCHEMA-KNOWLEDGE-BUILDER-033 切片合同

## Goal

实现一个不调用 LLM 的规则式知识构建器：从表名、字段名、声明类型、主键和外键元数据生成字段备注
初稿与候选业务术语；主库继续使用现有版本化知识，陌生 schema 自动使用构建结果，并只运行一次既有
15 题换库 HOLDOUT，和已封存的 `6/15` 基线如实比较。

## Non-goals

- 不修改第二库 schema、数据、15 个问题、reference SQL、expected 或判分口径。
- 不按单题写专用 SQL、关键词分支或结果修补；不修改 16 条训练对、意图门、工作流或安全边界。
- 不重复运行主库 40 题真实 Provider 评测；不补跑、不刷分、不把合成结果外推为生产准确率。
- 不新增依赖，不读取真实企业数据，不部署。

## Acceptance criteria

1. **WHEN** 输入合法 schema snapshot，**THEN** 构建器只用本地确定性规则生成版本化字段备注和候选
   术语，输出稳定排序，所有引用都存在于输入 schema，Provider 调用为 `0`。
2. **WHEN** 输入含不同命名的客户、商品和交易明细表，**THEN** 构建器能从标识符、类型、主外键识别
   订单号、客户、商品、日期、状态、渠道、数量、实际成交价、目录标价、区域和分群等通用角色。
3. **WHEN** 字段以 `_cents` 保存金额，**THEN** 自动备注与销售额 / 客单价候选术语明确金额需除以
   `100`；该规则不硬编码第二库题目或 SQL。
4. **WHEN** 输入重复表、重复字段、非法列或悬空外键，**THEN** 构建器失败关闭，不产出部分知识。
5. **WHEN** schema 完全由现有主库知识覆盖，**THEN** `build_business_context` 的术语、字段备注、枚举值
   和训练样例行为保持原合同；主库定向回归不降。
6. **WHEN** schema 含现有知识未覆盖字段，**THEN** 生成链使用自动知识；旧训练 SQL 不进入陌生 schema
   上下文，且只注入问题命中的候选术语和相关字段备注。
7. **WHEN** 对第二库运行离线定向测试，**THEN** 自动知识覆盖全部 16 个字段，关键问题得到数量、成交价、
   状态、渠道、订单、客户和商品的可用映射，HOLDOUT fixture 与 gold 字节不变。
8. **WHEN** 完成本地实现，**THEN** 自动构建器 / 两库定向测试、主库相关回归、Python 全量、编译、依赖、
   strict JSONL、园丁、治理、Web、Compose 和差异检查全绿。
9. **WHEN** 候选冻结后启动真实复测，**THEN** 15 题最多各进入 Provider 一次、自动重试 `0`；任何分数
   或 transport 结果均不补跑、不修改考场或候选。
10. **WHEN** 唯一复测结束，**THEN** 落盘 `6/15` 前后正确率、执行率、介入率、usage、逐类结果、越权 /
    非成功执行、数据库与报告哈希；远端精确 head 三 CI 全绿后 squash 合并并复核 main CI。

## Rollback

Revert 本切片提交即可移除自动构建器和生成链选择逻辑；现有静态知识、训练对、两套数据库与冻结评测
资产没有迁移。Git 忽略的唯一运行报告保留为历史回执。

## Rules restated

- 只做规则式 schema 知识自动构建；不得改第二库考场、单题调优、补跑或刷分。
- Provider 复测最多 15 次、自动重试 `0`；第一次完整结果无论升降即为最终结果。
- 主库继续使用既有知识；机械只读、审批、Provider 默认禁用与依赖方向不得变化。

## Reuse review

- 复用现有 `BusinessTerm` / `FieldDescription` 输出形状、问题匹配、严格 Provider JSON、工作流和评测器；
  不新增节点、工具或依赖。
- 复用 schema snapshot 已有的表、列、声明类型、主键和外键字段；自动构建器不读取业务行，也不猜测
  闭集枚举的实际存储值。
- 现有静态知识继续作为主库权威；只有 schema 出现未覆盖字段时才启用规则式候选，避免改变主库请求。

## Evidence

- `schema-derived-knowledge-v1` 对第二库 16 个字段生成一一对应备注，稳定输出 13 个候选术语；关键
  金额字段识别整数分缩放，状态备注明确不能臆造实际码，主外键关系进入字段说明。
- 自动知识定向 `6/6`；现有主库知识、枚举、训练对与 Provider 合同回归合计 `39/39`，fake transport
  证明自动上下文进入真实 Provider request shape，且陌生 schema 的训练样例为空。
- Python `3.13.12` 全量 106 项测试通过；编译与 44 包依赖、两份 strict JSONL、园丁 current
  `9/0/0`、治理、Web `2/2`、Compose config 与完整只读容器验收均通过。
- 容器第一次因 Windows CRLF 入口脚本以 `127` 退出；仅将本地脚本规范化为 Git blob 的 LF 后第二次
  达到 Healthy，验证完成后恢复原检出换行，最终 `deploy/container-entrypoint.sh` 代码 diff 为零。
- 本阶段未修改主 40 题、第二库、15 题 HOLDOUT、静态知识 JSON、16 条训练对、意图、Provider、
  工作流、依赖或 Compose；真实 Provider 调用、usage、token 与费用均为 `0`。

## Single-run HOLDOUT evidence

- 候选 `11b247773927e8d321e8fba3250070f63d05a381` 冻结后，唯一轮次
  `autoknowledge15-20260802T172429Z` 使用 HOLDOUT `3a598167…7bb16` 和第二库
  `ed9a2cda…78143d`；checkpoint / report 预先不存在，15 个 ID / 问题唯一。
- 15 题各保存一条 usage，transport 失败 `0`、自动重试 `0`，未补跑或修改候选 / 考场。基线 →
  本轮：执行 `0/7 → 3/7`、正确 `6/15 → 8/15`、介入 `2/15 → 5/15`；prompt / completion /
  total 为 `16434/999/17433 → 19635/1276/20911`。
- 成功 / 歧义 / 无答案 / 越权 / 注入正确数从 `0/7、0/2、2/2、2/2、2/2` 变为
  `0/7、2/2、2/2、2/2、2/2`。两条歧义恢复正确澄清，但 7 条成功仍全错；提升不能描述成成功
  查询泛化已解决。
- 三条成功 query 各执行一次只读 SQL并模拟审批，因错误状态码、金额单位 / 结果列行和无界审批判错；
  其余四条成功保守终止。越权与全部非成功执行为 `0`，业务库逐案例及整轮哈希不变。
- Git 忽略报告 `.local/model-eval-runner/runs/autoknowledge15-20260802T172429Z/report.json` 的
  SHA-256 为 `40ebf5b8720667c09da31e91e954003590ce3d1a6af2ba60ebaff9ae2811f8c3`，敏感模式命中 `0`。

## Remote evidence

远端流程完成后填写。
