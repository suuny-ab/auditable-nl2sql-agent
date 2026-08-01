# WORKFLOW-CORE-002：离线工作流与持久化轨迹

> 状态：`completed`
>
> 基线：本地提交 `7f7ab5c`，分支 `codex/offline-workflow-core`。

## 开工三问

- **做什么**：接入锁定版本的 LangGraph，以确定性 SQL stub 驱动现有 schema/只读执行能力；
  用独立 SQLite 保存 checkpoint，并从公开状态 API 投影稳定的 run/trajectory 合同。
- **不做什么**：不接 LLM/Provider，不做审批、恢复决策、自动重试、FastAPI、网页、Docker、
  Postgres 或完整评测集，不形成真实 NL2SQL 正确率主张。
- **怎样算完成**：成功、失败和独立进程回查路径全部有测试；业务数据库不变；依赖可在
  Python 3.13 干净安装；当前事实与证据回写项目状态。

## 验收合同

1. 生产路径包含 `load_schema → draft_sql → execute_sql → finish`；失败在当前节点终止。
2. 固定问题通过 stub 得到已验证 SQL，最终 run 为 `completed`、结果为 `5946.0`。
3. 注入无效 SQL 时 run 为 `failed/query_execution_error`，`attempt_count=1`，不自动重试。
4. 每个 run 使用独立 `run_id/thread_id`；trajectory 为项目自有 JSON 合同，不暴露框架内部表。
5. workflow/checkpoint SQLite 与只读业务 SQLite 物理分离；成功和失败后业务库 hash 均不变。
6. 关闭首个 runner 后，第二个独立 Python 进程能按 run ID 读回相同终态和有序 trajectory，
   且不会重新执行节点；这证明持久化回查，不冒充中断恢复。
7. SQLite checkpointer 显式禁用 pickle fallback，并拒绝任意 MessagePack 模块反序列化。
8. 精确顶层依赖和传递依赖锁进入仓库，CI 在 Python 3.13 从锁文件安装后运行全部测试。

## 状态与失败边界

- 状态：`received / schema_ready / sql_ready / executed / completed / failed`。
- 本切片自动重试固定为 `0`；执行尝试最多 `1` 次。
- 失败码至少包含：`schema_unavailable`、`unsupported_question`、`generator_error`、
  `read_only_violation`、`query_timeout`、`query_execution_error`、`unsupported_result_type`。
- 重复 run ID 失败关闭，不覆盖或续跑已有终态；真正幂等与恢复留给后续切片。

## 复用与架构决定

- 直接调用现有 `read_schema` 与 `execute_read_only`，不复制 SQL 安全逻辑。
- 使用 LangGraph `StateGraph` 和官方 `SqliteSaver`；不读取 checkpointer 私有表形成产品响应。
- checkpoint 保存恢复所需状态；项目 trajectory 作为 state 内的纯 JSON 事件列表，二者职责分开。
- 业务数据库只读，checkpoint 数据库可写；两个路径相同即拒绝启动。
- 采用探针验证过的候选组合：`langgraph==1.2.9`、
  `langgraph-checkpoint-sqlite==3.1.0`，传递版本由锁文件固定。

## 可证伪点

- 干净 Python 3.13 无法按锁安装，或 CI 只能依赖本机全局包。
- 第二进程必须重新执行节点才能获得结果，或 trajectory 依赖私有框架字段。
- checkpoint 表出现在业务库，或任一路径改变业务库 hash/schema/记录。
- 失败路径抛出未记录异常、自动重复执行，或被包装为 `completed`。

## 完成证据

- Python `3.13.12` 全新虚拟环境从 `api/requirements-base.lock` 以
  `--no-deps --require-hashes` 安装 38 个锁定包成功；`pip check` 通过。
- 完整 `unittest`：16/16 通过，耗时 `1.862s`；工作流定向测试 7 条、数据库回归 8 条、
  依赖合同测试 1 条。
- 成功终态为 `completed/5946.0`；无效 SQL 为 `failed/query_execution_error`；写 SQL 为
  `failed/read_only_violation`；均满足尝试上限和业务库 hash 不变。
- 第二个独立 Python 进程通过公开状态 API 读回完全相同的 run record，generator 未执行。
- 序列化器显式 `pickle_fallback=False`、`allowed_msgpack_modules=[]`；run record 可严格 JSON
  编码。编译、空白和公开内容扫描通过。
- [PR #1](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/1) 已合并为 `63381f9`；该 SHA
  的 Python 3.13 `main` CI 已通过。
- 未验证：正式产品内的中断恢复与人工决定、真实 LLM、FastAPI、Docker 或评测指标。
