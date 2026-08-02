# TRAINING-PAIR-RETRIEVAL-024 切片合同

## Goal

把冻结合成评测集中 8 条成功案例的“问题 → 参考 SQL”沉淀为版本化训练对，并在 Provider 生成
SQL 前按轻量相似度召回至有界业务上下文。

## Non-goals

- 不调用 Provider，不复跑 20 条冻结评测，不产生 token 或费用。
- 不做向量库、embedding、微调、记忆或技能，不增加依赖。
- 不改工作流结构、审批门、只读执行、评测口径或账户预算。
- 不接真实企业数据，不把训练对当安全边界或语义正确性的独立证明。

## Acceptance criteria

1. **WHEN** 加载训练对资源，**THEN** 严格验证 `training-pairs-v1`、8 个唯一成功案例、非空问题 / SQL
   与布尔 `enabled`，并由测试证明内容逐条等于冻结评测成功案例。
2. **WHEN** 问题与启用训练对的规范化字符二元组 Jaccard 相似度不低于 `0.72`，**THEN** 按分数
   降序、案例 ID 稳定排序，最多召回 2 条到 `business-context-v2.training_examples`。
3. **WHEN** 相似度低于阈值，**THEN** `training_examples` 为空，不注入无关 SQL。
4. **WHEN** 训练对 `enabled=false`，**THEN** 即使问题完全相同也不得召回。
5. **WHEN** Provider 构造请求，**THEN** 训练对只作为可信只读参考模板，原 schema、业务术语、字段
   备注和机械安全边界保持不变。
6. **WHEN** 完成实现，**THEN** 三条定向路径、全量测试、compileall、依赖、治理、园丁、Compose
   与差异检查全部通过，真实 Provider 调用为 0。
7. **WHEN** 候选推送并创建 Draft PR，**THEN** 只使用本单一次授权；精确 head 的 web / api /
   container CI 全绿后按常设档 squash 合并，并复核 main CI。

## Rollback

回滚本切片提交即可删除训练对资源、召回函数与上下文字段；Provider 会恢复为只注入术语和字段
备注。训练对不写数据库、不改变 checkpoint，也没有外部数据迁移。

## Rules restated

- 产品代码不得导入 `evals`；训练对与冻结评测的一致性由测试从独立事实源验证。
- Provider 默认禁用，本切片禁止真实调用和评测复跑；静态模板不能绕过只读执行与审批门。
- 只使用明确标注的合成数据；本单只允许一次候选 push 和一次 Draft PR 创建。

## Local evidence

- `training_pairs.json` 严格加载 8 条 `success-001` 至 `success-008`；独立测试从
  `evals/cases.jsonl` 读取冻结合同，逐条比较 source ID、问题和 SQL，全部一致且默认启用。
- 相似问句以 `0.8571` 命中 `success-001`；无关天气问题无命中；把同一训练对切到
  `enabled=false` 后，完全相同问题也返回空列表。Provider fake transport 证明命中项进入
  `business-context-v2.training_examples`，并保留只读参考 / 不覆盖安全规则提示。
- Python `3.13.12` 全量 `74` 项、Web 生产构建与 2 项 SSR 通过；`compileall`、44 包依赖、strict
  JSON、Compose config、治理和 `git diff --check` 通过；wheel 包含术语、字段备注与训练对三份
  JSON。园丁 current `9/0/0`，all
  `31/stale=0/review=8`，后者均为既有历史相对时态复核项。
- 本地执行只使用 fake transport；真实 Provider 调用、token、费用、评测报告、数据库写入和工作流
  改动均为 `0`。
