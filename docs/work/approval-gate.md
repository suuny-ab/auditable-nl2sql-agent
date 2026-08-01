# APPROVAL-GATE-004

> 状态：`completed`
>
> 日期：`2026-08-01`
>
> 基线：`63381f95359fb3bd605e0a1d2f21ef1480a3b713`

## 做什么

- 在 SQL 生成与正式执行之间增加机械查询校验和审批节点。
- 默认审批阈值为 5 行：明确请求超过阈值的结果集进入 `pending_approval`；单行聚合和不超过
  阈值的显式 `LIMIT` 可直接执行。
- 写操作或特权 SQL 进入审批挂起，但状态标记为不可批准执行；即使收到批准决定也以失败终态
  结束，不能到达 SQL 执行节点。
- `WorkflowRunner.decide(...)` 使用同一 run ID 和 SQLite checkpoint 恢复批准或拒绝决定。
- 已终结 run、缺失 run、非法 decision ID 和非法决定必须显式失败关闭。
- 稳定 run record 和 trajectory 记录审批原因、阈值、决定 ID、决定与终态。

## 不做什么

- 不接 LLM、Provider、FastAPI、网页、Docker、Postgres 或完整评测。
- 不实现真实用户身份、角色权限矩阵、并发审批者竞争或分布式 exactly-once。
- 不实现通用 SQL 优化器或精确结果行数估算；本切片采用保守 SQL 形状策略，机械只读边界仍由
  SQLite URI、`query_only` 和 authorizer 提供。
- 不让人工批准放宽执行器的只读、行数或超时限制。
- 不自动重试。

## 怎样算完成

- 普通单行聚合无需审批并保持原有成功结果。
- `LIMIT 6` 在阈值 5 下持久化为 `pending_approval`，执行尝试为 0；重启进程后批准只执行一次。
- 另一个挂起 run 被拒绝后为 `rejected`，执行尝试为 0。
- 已完成或已拒绝 run 的重复决定显式抛出产品异常，trajectory 和业务结果不变化。
- 写 SQL 先挂起；批准后为不可绕过只读边界的失败终态，执行尝试为 0，业务库哈希不变。
- 原有无效 SQL、未知问题、缺失 schema、重复 run 和只读数据库测试继续通过。
- 每条审批路径均可跨进程按 run ID 回查稳定 JSON record；完整测试、编译、依赖和公开内容检查
  通过。

## 设计约束

- 查询合法性和写操作识别使用 SQLite `EXPLAIN QUERY PLAN` 配合现有 authorizer，不把字符串
  判断当作只读安全边界。
- 行数策略只识别保守安全形状：无 `GROUP BY/UNION` 的单行聚合，或结尾处简单字面量
  `LIMIT n`。其他结果集默认要求审批。
- LangGraph 对已终结 run 的重复 `Command(resume=...)` 是静默 no-op；产品 runner 必须在恢复
  前检查当前状态，显式拒绝重复决定。

## 证据

- `EXPLAIN QUERY PLAN` 与现有 SQLite authorizer 的机械探针中，合法 SELECT 只生成查询计划；
  `DELETE` 和 `PRAGMA` 得到 `not authorized`；无效字段得到明确 SQLite 错误。
- 默认阈值 5 下，`LIMIT 6` 得到 `pending_approval`、执行尝试 `0`；第二个真实 Python 进程
  使用同一 run ID 批准后得到 `completed`、6 行结果和执行尝试 `1`，generator 未重新运行。
- 已完成 run 的重复决定抛出 `InvalidApprovalDecisionError`，前后稳定 run record 完全相同。
- 拒绝路径得到 `rejected/approval_rejected`、执行尝试 `0`；非法布尔值、非法 decision ID、
  缺失 run 和终态重复决定均失败关闭。
- 写 SQL 先挂起且 `can_execute=false`；批准后得到
  `failed/approval_cannot_override_read_only`、执行尝试 `0`，未到达执行节点。
- 普通单行聚合和 `LIMIT 5` 直接完成；无字面量上限的多行查询保守进入审批。
- 数据库与工作流定向测试及依赖合同共 20 项通过；业务库哈希比较、严格 JSON 投影和第二进程
  恢复测试通过。[Draft PR #2](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/2)
  当前 HEAD 的远端 CI 结论为 `success`，PR 未获得合并授权。
