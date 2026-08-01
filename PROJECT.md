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
- 离线工作流核心和审批门已分别由 PR #1、PR #2 合并到 `main`；当前 `main@d7be385` 的
  20 个测试与远端 CI 通过。

真实模型生成、业务语义校验、自然语言回答、真实身份权限、FastAPI、网页、评测集和 Docker
仍待实现。当前 evidence 指纹不是数字签名，也不证明 SQL 的业务语义正确。
