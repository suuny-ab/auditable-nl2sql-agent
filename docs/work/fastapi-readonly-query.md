# FASTAPI-READONLY-QUERY-014 任务书

## Goal

让后续最小网页能够通过 FastAPI 只读列出已持久化的运行摘要，并按 run ID 回查包含完整
trajectory 的稳定 `run-record-v5`，查询过程不修改业务库或 checkpoint。

## Non-goals

- 不新增创建运行、人工审批、重跑、删除或任何其他 `POST` / `PUT` / `PATCH` / `DELETE` 能力。
- 不调用 Provider，不读取凭据，不调整 prompt、评测集、模型基线或产品安全边界。
- 不做网页、Docker、部署、鉴权、真实用户身份、Postgres、流式接口或异步工作流。
- 不把 LangGraph checkpoint 原始结构作为 HTTP 合同；API 只返回项目自有的版本化投影。
- 不顺手修复首次模型基线中的 6 条误差，不增加新的业务表或工具。

## AC

1. **WHEN** checkpoint 中存在多个已持久化 run，**THEN** `GET /api/v1/runs` 返回
   `run-list-v1`，按最近 checkpoint 从新到旧给出稳定摘要、总数和有界分页字段。
2. **WHEN** 客户端请求已存在的合法 run ID，**THEN** `GET /api/v1/runs/{run_id}` 返回原样的
   `run-record-v5`，其中包含完整有序 trajectory、审批、evidence 和 answer 字段。
3. **WHEN** run ID 合法但不存在，**THEN** API 返回 `404` 和稳定错误信息，不泄露文件路径、
   SQL 异常或 checkpoint 内部结构。
4. **WHEN** run ID 格式非法，或 `limit` 不在 `1..100`、`offset < 0`，**THEN** API 返回
   `422`，且不查询或修改运行状态。
5. **WHEN** 对任一只读路由发送 `POST`，**THEN** API 返回 `405`；应用不注册运行、审批、
   Provider 或数据库写入路由。
6. **WHEN** 依次执行列表、成功详情、缺失详情和非法输入查询，**THEN** 合成业务数据库与
   checkpoint SQLite 的 SHA-256 均保持不变，已有 run 的状态和执行次数不变。
7. **WHEN** 在 Python 3.13 CI 合同下安装依赖，**THEN** FastAPI 使用精确版本并同时出现在
   `api/pyproject.toml`、`api/requirements-base.txt` 与 hash lock 中。
8. **WHEN** 运行 API 定向测试和现有全量测试，**THEN** 成功路径与对应失败关闭路径全部通过，
   `compileall`、`pip check` 和 `git diff --check` 通过。

## 回滚

回滚本切片的单一本地提交；这会同时移除 API 模块、只读列表投影、测试、FastAPI 依赖锁和
本任务状态记录，不触碰既有 checkpoint 或合成业务数据库。

## 规则复述

- 生产依赖方向保持 `API → workflow → tools/data`；本切片不允许 workflow 反向导入 API。
- SQL 与审批机械安全边界不变；HTTP 查询不能创建、恢复或决定 run，人工批准也不能借 API
  绕过只读执行器。
- 只使用明确标注的合成数据；Provider 默认禁用，本切片真实 Provider 调用、凭据读取和费用均为
  `0`。

## 复用审查

- 直接复用 `WorkflowRunner.get_run()` 的 `run-record-v5`，不在 API 层复制 trajectory、
  evidence 或 answer 的业务投影规则。
- 在 workflow 层增加最薄的 `list_runs()` 摘要投影；API 只负责参数校验与 HTTP 状态映射。
- FastAPI 作为 PROJECT.md 已冻结的 MVP 依赖引入；不同时引入 Uvicorn、前端或部署依赖。

## 验证证据

- `GET /api/v1/runs` 返回 `run-list-v1` 的新到旧摘要、`total`、`limit` 和 `offset`；
  `GET /api/v1/runs/{run_id}` 直接返回既有 `run-record-v5`，不复制 trajectory/evidence/answer
  投影逻辑。
- `WorkflowRunReader` 用 SQLite URI `mode=ro` 和 `PRAGMA query_only=ON` 打开既有 checkpoint，
  并且不暴露 `run()` 或 `decide()`；对底层 checkpoint 的直接删除尝试得到 `readonly` 拒绝，缺失
  checkpoint 也不会被查询动作创建。
- API 定向 4 项测试通过：列表与分页、完整详情、404/422/405、reader 机械只读；写入 runner
  关闭后再创建 reader，reader 构造前后及全部 HTTP 查询后的业务库和 checkpoint SHA-256 均不变。
- Python `3.13.12` 全量 49 项测试通过；`compileall`、`pip check`、`git diff --check`、
  `.local` 跟踪文件和产品反向导入检查通过。
- FastAPI 精确固定为 `0.139.2`，已进入 pyproject、直接依赖输入和 hash lock；版本选择依据
  [PyPI 的 2026-07-16 发布记录](https://pypi.org/project/fastapi/)。本轮真实 Provider 调用、凭据
  读取和 token 消耗均为 `0`。
