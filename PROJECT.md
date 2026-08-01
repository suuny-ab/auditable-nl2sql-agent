# 项目事实

> 项目：`auditable-nl2sql-agent`
>
> 状态：`mvp_development`
>
> 最后核实：`2026-08-01`

## 产品目的

这是一个面向求职作品集的可审计企业数据问答 Agent。用户用自然语言提问，受约束的
LangGraph 工作流生成 SQL，在只读沙箱中执行，并把查询、结果、证据和人工审批状态绑定到
同一次运行中。

目标演示是在两分钟内呈现：问题、生成 SQL、执行结果、证据链、一条被审批门拦截的高危
查询，以及固定合成评测集的数字。

## MVP 边界

- 电商销售域 3–5 张合成数据表；默认 SQLite，可选 Postgres。
- LangGraph 状态机覆盖意图、SQL 生成、执行、校验和回答，并定义失败重试与断点恢复边界。
- 最多 5 个工具：schema 读取、只读 SQL 执行、结果校验、证据绑定、审批门。
- 写操作、超行数和越权查询进入失败关闭或人工审批；至少一条权限拒绝路径。
- 约 20 条合成评测，覆盖成功、歧义、无答案、越权和注入；保存结构化 trajectory。
- FastAPI、Docker 一键启动，以及只含任务列表和轨迹查看的最小网页。

## 不可牺牲边界

- 只用合成数据，不接真实企业数据库或公司内部材料。
- 数据库执行层保持只读；模型输出和人工批准都不能绕过机械安全边界。
- 回答中的数据结论必须能回查到 SQL、结果和 schema/行级证据。
- Provider、费用、凭据、外部写入和公开发布默认不授权。
- 不把 BI 大屏、多 Agent、微调、大 schema 或与 Traceable 的系统集成纳入 MVP。

## 当前能力

- 公开源码仓库为 <https://github.com/suuny-ab/auditable-nl2sql-agent>；公开不代表 MVP 已完成。
- 可重复创建 4 表、共 26 行记录的合成电商 SQLite 数据库，且拒绝覆盖已有数据库文件。
- schema 读取返回用户表、字段、主键和外键，不暴露 SQLite 内部表。
- SQL 执行同时受 URI `mode=ro`、`query_only` 和 SQLite authorizer 约束，并限制返回行数和
  本地执行时间；写入、DDL、`ATTACH` 和 `PRAGMA` 失败关闭。
- 首切片 8 个测试已在本地和首次 GitHub Actions 中通过；这只证明 SQLite 事实层，不是完整
  NL2SQL 或 Agent 能力。
- 确定性 LangGraph 工作流已串联 schema、SQL stub、审批门和只读执行；成功、无效 SQL、
  审批拒绝、写操作拒绝、未支持问题及缺失 schema 都形成持久化终态。
- LangGraph checkpoint 写入独立 workflow SQLite；项目自有 JSON trajectory 随状态保存，
  第二个独立 Python 进程可按 run ID 回查而不重新执行节点。
- 高行数只读 SQL 和机械只读校验拒绝的 SQL 会在执行前进入 `pending_approval`；另一进程可用
  同一 run ID 批准或拒绝。已终结 run 的重复决定显式失败，批准不能让写 SQL 到达执行节点。
- SQL 结果会校验列名、行宽、截断状态和严格 JSON 标量；截断或结构异常失败关闭，不产生
  evidence。
- 成功结果绑定 run ID、问题、SQL、schema 快照、结果与校验回执，形成版本化
  `evidence-v1`；规范 JSON 的 SHA-256 可在独立进程重算验证。
- 通过完整 evidence 合同校验后生成 `answer-v1`：单行结果精确引用结果单元格，零行和多行
  只生成 evidence 直接支持的保守摘要；回答与 trajectory 可按 run ID 跨进程回查。
- 已冻结 20 条合成评测合同，按成功、歧义、无答案、越权、注入分为 `8/3/3/3/3`；成功与
  越权参考 SQL 可由现有工作流复算，但尚未运行真实模型或产生指标。
- DeepSeek 最小探针使用 `deepseek-v4-flash` 对 2 条成功问题和 1 条删除请求得到严格 JSON；
  加入稳定输出列合同后，两条只读 SQL 的结果命中 gold，删除请求在模型层阻断且执行次数为 0。
  这只证明当前凭据、接口和最小安全路由可行，不是正式 Provider 或模型评测能力。
- 正式 `DeepSeekSqlGenerator` 默认禁用，显式启用后读取环境凭据；严格校验 JSON plan 与 usage，
  并把脱敏 Provider 回执写入 trajectory。真实收入查询已完成 evidence/answer，真实删除请求在
  `draft_sql` 阶段阻断且执行次数为 0；仍未产生 20 条评测指标。
- 候选五类 Provider action 的最小探针中，歧义、无答案、越权删除和提示词注入 4 条真实调用
  分别得到 `clarify`、`no_answer`、`unsafe_operation`、`block`；所有执行次数为 0，业务库不变。
  该探针本身只排除了分类可分性的最小风险，不代表正式决策终态合同或模型评测指标已经实现。
- 正式 Provider plan 已支持五类 action；`run-record-v5` 直接投影 `provider_action`，并把
  `clarify`、`no_answer`、`block` 持久化为独立零执行终态。`unsafe_operation` 携带审计 SQL，
  但 action 本身固定进入 `can_execute=false` 的审批；人工批准仍不能触发执行。
- 离线工作流核心、审批门、结果证据、确定性回答、固定评测合同和 Provider 探针已分别由
  PR #1 至 PR #6 合并到 `main`；探针 merge commit `604ccf4` 的 33 个测试与远端 CI 通过。

业务语义评测、真实身份权限、FastAPI、网页、模型评测运行与指标、Docker
仍待实现。当前 answer 是确定性结果投影；evidence 指纹不是数字签名，也不证明 SQL 的业务
语义正确。
