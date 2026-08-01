# PROVIDER-DECISION-CONTRACT-012

> 状态：`completed`
>
> 日期：`2026-08-01`
>
> 基线：`852dca724812d5dae8c8a1d0bdc70f1a28dabf83`

## 做什么

- 把严格 Provider plan 扩展为 `query`、`unsafe_operation`、`clarify`、`no_answer`、`block`
  五类 action。
- `query` 与 `unsafe_operation` 必须携带 SQL；其余三类必须使用 `sql=null`。
- 将 `clarify`、`no_answer`、`block` 分别持久化为 `clarification_required`、`no_answer`、
  `blocked` 稳定终态，执行次数为 0。
- 将 `unsafe_operation` SQL 持久化并送入现有审批路径，固定 `reason=unsafe_operation`、
  `can_execute=false`；人工批准仍不能进入执行节点。
- 将 `provider_action` 加入版本化 run record 投影，供评测器直接读取；保留脱敏 Provider 回执。
- 使用 fake transport 覆盖五类 action、合同漂移、稳定终态和机械只读兜底。

## 不做什么

- 不调用真实 Provider，不运行完整 20 条模型评测，不计算或公开指标。
- 不实现评测运行器、FastAPI、网页、Docker、异步、流式或 Provider 选择界面。
- 不新增依赖、工具、业务表、代码层预算或自动重试。
- 不改变 SQLite 只读连接、authorizer 或“人工批准不能越过只读边界”的规则。
- 不推送、不创建或修改 PR、不合并远端分支。

## 怎样算完成

- 严格解析接受五类合法 action，并拒绝缺失 SQL、错误携带 SQL、未知 action 和其他合同漂移。
- `clarify`、`no_answer`、`block` 的 run record 含精确 `provider_action` 和稳定终态，且
  `generated_sql=null`、`attempt_count=0`、无 approval/evidence/answer。
- `unsafe_operation` 的 run 先成为 `pending_approval`，审批字段为
  `reason=unsafe_operation`、`can_execute=false`；批准后以
  `approval_cannot_override_read_only` 结束，执行次数仍为 0。
- 即使 Provider 把删除 SQL 错标为 `query`，现有机械校验仍能阻断；业务数据库哈希在所有安全
  路径前后不变。
- Provider 定向测试、全量测试、编译、依赖、差异、凭据模式和依赖方向检查全部通过。

## 复用与设计边界

- 复用现有 `DeepSeekSqlGenerator`、`WorkflowRunner`、审批门和脱敏 trajectory，不增加新工具或
  第二套路由。
- `provider_action` 属于 run record 的可审计决策字段；终态由工作流写入，评测层只读取，不反向
  解释内部异常文本。
- `unsafe_operation` 是可审计但不可执行的模型决定；`block` 专用于注入、绕过规则或改变系统指令
  的请求，两者已由 `PROVIDER-DECISION-PROBE-011` 的真实调用验证可分。

## 声明边界

- 本切片证明产品合同和机械路由，不证明模型在 20 条评测集上的准确率。
- fake transport 只验证确定性工程合同；真实 Provider 可用性沿用已完成探针，不在本轮重复消费。

## 验证证据

- `DeepSeekSqlGenerator` 严格接受五类 action；`query` 与 `unsafe_operation` 必须携带 SQL，
  `clarify`、`no_answer`、`block` 必须使用 `sql=null`，合同漂移继续失败关闭。
- run record 升级为 `run-record-v5` 并投影 `provider_action`；三类无 SQL 决策分别持久化为
  `clarification_required`、`no_answer`、`blocked`，执行次数均为 0，且无 approval/evidence/answer。
- `unsafe_operation` 即使携带机械上可读的 SQL，也固定进入 `reason=unsafe_operation`、
  `can_execute=false` 的审批；模拟批准后以 `approval_cannot_override_read_only` 结束，执行次数为 0。
- Provider 把 `DELETE` 错标为 `query` 时，SQLite 机械校验仍以 `read_only_violation` 要求不可执行
  审批；模拟批准后执行次数仍为 0。两条安全测试均断言业务数据库 SHA-256 前后相同。
- Python `3.13.12` Provider 定向测试 10 项、全量产品与合同测试 43 项通过；`compileall`、
  `pip check`、`git diff --check`、tracked secret pattern scan、`.local` 未跟踪检查和产品不反向导入
  `evals` 检查通过。
- 本轮使用 fake transport，真实 Provider 调用次数和 token 消耗均为 0；未新增依赖、工具或费用逻辑。
- [Draft PR #8](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/8) 已创建；
  [CI run 30693992922](https://github.com/suuny-ab/auditable-nl2sql-agent/actions/runs/30693992922)
  在 publication head `e103dc5` 上完成，结论为 `success`。
