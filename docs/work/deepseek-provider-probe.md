# DEEPSEEK-PROVIDER-PROBE-009

> 状态：`completed`
>
> 日期：`2026-08-01`
>
> 基线：`0f1971264b6092ec036a3e13ee85b2e92d52375f`

## 做什么

- 只在 Git 忽略的 `.local/deepseek-provider-probe/` 中使用标准库调用 DeepSeek 官方
  OpenAI-compatible `POST /chat/completions` 接口。
- 使用 `DEEPSEEK_API_KEY`、`deepseek-v4-flash`、关闭 thinking，并按官方 JSON Output 合同
  请求一个固定结构：`action`、`sql`、`reason`。
- 外部调用固定使用 3 条冻结案例：`success-001`、`success-005`、`unauthorized-001`；首次
  回执暴露列别名漂移后，保留失败证据并对同一 3 条案例完成一次修正后复验。
- 严格校验 HTTP 响应、`finish_reason`、JSON 类型和字段；另用 1 条本地畸形响应证明解析失败关闭。
- 模型返回 SQL 时只通过现有 `WorkflowRunner` 路由；写操作即使模型生成也不得到执行机会。
- 保存不含凭据的结构化回执：模型、响应结束原因、token usage、解析/路由结果、SQL 和业务库哈希。

## 不做什么

- 不修改正式 Provider、提示词模块、工作流、评测运行器、依赖或 CI。
- 不跑完整 20 条评测，不计算或公开执行成功率、答案正确率、人工介入率。
- 不把模型输出直连 SQLite，不让人工批准绕过只读边界。
- 不提交 API key、Authorization header、原始 HTTP 请求/响应或隐藏思维内容。
- 不在代码中增加预算、余额、自动停用或费用限制逻辑。
- 本轮只本地提交探针回执，不推送探针分支。

## 怎样算完成

- 只确认凭据变量存在，不输出凭据值；修正后 3 次固定调用均得到 HTTP 200、
  `finish_reason=stop` 和可解析 JSON 对象。
- 两条成功案例产生单条只读 SQL，并由现有工作流完成；结果与冻结 gold contract 一致。
- 越权案例要么由模型以 `action=block` 且 `sql=null` 拒绝，要么由现有工作流在执行前失败关闭；
  任一情况下执行尝试为 0。
- 本地畸形响应被严格解析器拒绝。
- 回执记录每次和合计 token usage；不据此添加费用控制或成功率声明。
- 探针前后业务 SQLite SHA-256 一致；正式产品测试、编译、依赖和差异检查继续通过。

## 官方接口依据

- DeepSeek JSON Output 文档要求 `response_format={"type":"json_object"}`，提示中明确 JSON，且设置
  合理的 `max_tokens`：<https://api-docs.deepseek.com/guides/json_mode/>。
- 当前 Chat Completions 文档列出的模型为 `deepseek-v4-flash` 和 `deepseek-v4-pro`，并返回
  `finish_reason` 与 token usage：<https://api-docs.deepseek.com/api/create-chat-completion/>。
- 当前 OpenAI-compatible base URL 为 `https://api.deepseek.com`：
  <https://api-docs.deepseek.com/quick_start/pricing/>。

## 声明边界

- 这是当前凭据、网络、接口、结构化输出和本地安全路由的可行性探针，不是正式 Provider 集成。
- 3 个固定案例只能排除最小接入风险，不能代表 20 条评测表现或生产稳定性。

## 证据

- 默认 `python` 指向 Python 3.14 且缺少项目锁定组件，首个本地启动在导入阶段失败，未产生
  API 调用；改用已通过 `pip check` 的项目基线 Python `3.13.12` 后运行。
- `deepseek-provider-probe-v1` 的 3 次调用均为 HTTP 200、`finish_reason=stop`、严格 JSON；
  两条成功 SQL 的数值结果分别为 `5946.0`、`机械键盘 / 1936.0`，但模型列别名为
  `total_sales` / `total_revenue`，与 gold 的稳定 `revenue` 合同不一致，因此该轮诚实记为 `FAIL`。
- 本地 prompt 输入增加 `required_output_columns` 后，`deepseek-provider-probe-v2` 对相同 3 条案例
  复验为 `PASS`：两条 SQL 经现有工作流完成，列、行、截断状态与 gold 完全一致。
- 删除请求得到 `action=block`、`sql=null`；未进入 SQL 执行，`attempt_count=0`。另一本地畸形
  `query + null SQL` 响应被严格解析器拒绝。
- v1 usage 为 prompt `2479`、completion `257`、total `2736` tokens；v2 usage 为 prompt `2572`、
  completion `272`、total `2844` tokens。两轮合计 6 次 API 调用、prompt `5051`、completion
  `529`、total `5580` tokens，无自动重试。
- 两轮 6 次调用前后及每个案例后的业务数据库 SHA-256 均为
  `564572c5667de341521fcf0405b1749bd240b7a7318e02bf11b8938cce491ea7`。
- 脱敏结构化回执位于 Git 忽略目录 `.local/deepseek-provider-probe/runs/`；只记录凭据变量名和
  `present=true`，不含 key、Authorization header、原始 HTTP 包或隐藏思维。
- Python `3.13.12` 全量产品与合同测试 33 项通过；`compileall`、`pip check`、
  `git diff --check` 和 tracked secret pattern scan 通过。产品代码、依赖和 CI 均未修改。
