# DEEPSEEK-SQL-GENERATOR-010

> 状态：`completed`
>
> 日期：`2026-08-01`
>
> 基线：`604ccf4cae3a85970559bcfe99775e0871140217`

## 做什么

- 新增标准库实现的 DeepSeek Chat Completions transport，固定使用官方 HTTPS endpoint，不增加依赖。
- 新增默认禁用的 `DeepSeekSqlGenerator`；只有调用方显式启用时才读取 `DEEPSEEK_API_KEY`。
- 请求严格 JSON `action/sql/reason`；校验 HTTP envelope、单一 choice、`finish_reason=stop`、
  token usage 和精确 plan 字段。
- `query` 返回 SQL 与脱敏 Provider 回执；`block`、`clarify`、`no_answer`、transport 失败和响应
  合同错误以稳定错误码在 `draft_sql` 失败关闭。
- 将 Provider、模型、action、finish reason 和 token usage 写入现有 trajectory；不保存 key、header、
  原始 HTTP 包或隐藏思维。
- 使用可注入 fake transport 测试成功、模型阻断、畸形响应、网络错误和危险 SQL 的机械兜底。
- 在 Git 忽略目录用当前已授权的环境变量完成 1 条成功问题和 1 条删除请求的真实冒烟；不自动重试。

## 不做什么

- 不运行完整 20 条模型评测，不计算或公开成功率、正确率、人工介入率。
- 不实现 FastAPI、网页、Docker、Provider 选择 UI、异步或流式调用。
- 不做大规模提示词优化，不新增业务 schema、工具或第三方依赖。
- 不改变 SQLite 机械只读边界，不让模型 action 或人工批准覆盖 authorizer。
- 不在代码中实现预算、余额、费用告警或自动停用逻辑。
- 不合并 PR，不把 Draft PR 转为 Ready；外部发布只到用户当次授权的切片分支和 Draft PR。

## 怎样算完成

- 未显式启用时不读取凭据、不调用 transport，工作流默认继续使用 `StaticSqlGenerator`。
- 严格响应产生的只读 SQL 经现有工作流完成，并生成可验证 evidence 与 `answer-v1`；Provider 回执
  可从同一 run trajectory 回查。
- `block`、畸形 JSON、非 `stop`、usage 漂移和 transport 错误均停在 `draft_sql`，执行次数为 0，
  不产生 approval、evidence 或 answer。
- 即使 Provider 把删除语句标为 `query`，现有审批门仍固定 `can_execute=false`；模拟批准后执行次数
  仍为 0。
- 真实成功冒烟完成并得到 evidence/answer；真实删除请求不执行。两次调用均记录 usage，业务库
  SHA-256 前后相同。
- 原有测试继续通过；新增测试、编译、依赖、差异和凭据模式检查通过。

## 复用与设计边界

- 复用现有 `SqlGenerator` 注入点、`WorkflowRunner`、审批门、只读执行、evidence 和 answer，
  不复制第二套工作流。
- 复用最小探针验证过的官方 JSON Output 请求形状；正式实现使用标准库 `urllib`，避免为一个同步
  endpoint 新增 SDK 依赖。
- `SqlGenerator` 继续兼容返回字符串的测试替身；正式 Provider 返回带脱敏审计回执的类型化结果，
  由 `draft_sql` 投影进 trajectory。

## 声明边界

- 本切片证明正式 Provider adapter 的最小闭环，不代表 20 条评测表现或生产稳定性。
- 模型级 `block` 是第一层失败关闭；SQLite URI、`query_only` 和 authorizer 仍是不可替代的最终边界。

## 证据

- 新增 `provider.py`：默认禁用的 generator、显式环境凭据工厂、固定官方 HTTPS transport、严格
  response/plan/usage 解析、类型化错误和 `provider-receipt-v1`；未新增依赖。
- 现有 `SqlGenerator` 继续接受字符串替身；类型化 Provider 结果或失败的脱敏回执由 `draft_sql`
  写入同一 trajectory，默认 `WorkflowRunner` 行为未改变。
- 8 项 Provider 定向测试通过：默认禁用、成功回执、三类模型决定、8 类响应漂移、错误脱敏、
  完整 evidence/answer、三类零执行失败，以及危险 SQL 的机械兜底。
- 两条真实固定冒烟均无重试：收入查询生成 `revenue=5946.0`，完成 evidence 与 answer；删除请求
  得到 `provider_blocked`、`generated_sql=null`、`attempt_count=0`，不产生 approval/evidence/answer。
- 两次真实调用 usage 合计 prompt `1674`、completion `141`、total `1815` tokens；业务库冒烟
  前后 SHA-256 均为 `564572c5667de341521fcf0405b1749bd240b7a7318e02bf11b8938cce491ea7`。
- 真实回执保存在 Git 忽略目录 `.local/deepseek-sql-generator-smoke/runs/20260801T083031Z/`；只记录
  合成问题、SQL、结果、脱敏 Provider receipt 和数据库哈希，不含凭据或原始 HTTP 数据。
- Python `3.13.12` 全量产品与合同测试 41 项通过；`compileall`、`pip check`、
  `git diff --check`、tracked secret pattern scan、`.local` 未跟踪检查和产品不反向导入 `evals`
  检查通过。
- [Draft PR #7](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/7) 已创建；
  [CI run 30692232491](https://github.com/suuny-ab/auditable-nl2sql-agent/actions/runs/30692232491)
  在 implementation SHA `120a458` 上完成，结论为 `success`。
