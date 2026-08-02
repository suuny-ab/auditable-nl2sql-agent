# READONLY-API-HEALTH-015

## Goal

让现有 FastAPI 只读查询核心可以用一条明确命令独立启动，并用 health 接口暴露服务版本与只读状态。

## Non-goals

- 不新增 run 创建、审批决定或任何数据库写接口。
- 不调用 Provider，不读取凭据，不增加代码层费用逻辑。
- 不做鉴权、网页、Docker、部署、公开发布或生产就绪主张。
- 不改变现有 run list/detail 与 `run-record-v5` 合同。

## Acceptance criteria

1. **WHEN** 操作者提供已存在的合成业务库与 checkpoint 路径，**THEN** 文档中的
   `auditable-nl2sql-api` 命令能在指定 host/port 独立启动 HTTP 服务。
2. **WHEN** 服务已启动，**THEN** `GET /api/v1/health` 返回固定 schema、服务版本、
   `status=ok` 与 `read_only=true`。
3. **WHEN** 服务由启动装配创建，**THEN** 现有 run list/detail 路由复用
   `WorkflowRunReader`，且 lifespan 结束时关闭 reader。
4. **WHEN** 业务库或 checkpoint 不存在，**THEN** 服务启动失败关闭且不创建缺失文件。
5. **WHEN** 客户端向 health 或 run 路由发送写方法，**THEN** 返回 `405`，应用仍不注册
   run 创建、审批或 Provider 路由。
6. **WHEN** 执行 health 与 run 查询，**THEN** 合成业务库和 checkpoint 的 SHA-256 均不变。
7. **WHEN** 在 Windows 与 Linux Python 3.13 合同下安装依赖，**THEN** Uvicorn 及其
   Windows 运行依赖使用精确版本，并同时出现在 `api/pyproject.toml`、
   `api/requirements-base.txt` 和 hash lock 中。
8. **WHEN** 执行全量测试、编译、依赖一致性与差异检查，**THEN** 所有检查通过。

## Rollback

回滚本切片的单一本地提交；这会同时移除启动器、health 路由、启动冒烟测试、Uvicorn 依赖和
对应文档，不影响已合并的只读查询 API。

## 本场规则复述

- 本切片只交付独立启动与 health；新增想法进入候选队列，不直接实现。
- SQL/运行记录访问继续同时依赖数据库只读连接与机械授权边界，health 不得引入写路径。
- Provider 默认禁用；本切片 Provider 调用、凭据读取、费用和外部公开动作均为零。

## 复用审查

- 复用现有 `create_app`、`WorkflowRunReader` 和稳定 run record，不另建查询层。
- 采用 FastAPI lifespan 绑定 reader 的打开/关闭，采用 Uvicorn 的 Python API 承载现有 ASGI app。
- Uvicorn 精确固定为 `0.52.1`；版本取自 2026-08-01 的官方 PyPI 发布记录。
- Linux 目标 lock 不会解析 Click 的 Windows 条件依赖，因此显式固定 `colorama==0.4.6`，保证
  Windows 安装同一 lock 后 `pip check` 也通过。

## Evidence

- Python `3.13.12`：启动器定向 `3` 项、全量 `53` 项测试通过。
- 真实子进程使用 README 的 `python -m auditable_nl2sql.server` 命令启动 Uvicorn，health 与
  `run-record-v5` 回查均成功；进程关闭后 reader 固定报告已关闭。
- 缺失业务库/checkpoint 均在监听前失败且不创建文件；查询前后双库 SHA-256 不变。
- `uvicorn==0.52.1` 与 `colorama==0.4.6` 已进入 pyproject、直接依赖输入和 hash lock；
  Windows Python 3.13 `pip check` 为 `No broken requirements found`。
- `compileall`、CLI `--help`、`git diff --check`、`.local` 跟踪、可变 HTTP 路由和产品反向导入
  检查通过；Provider 调用、凭据读取、token 消耗与费用均为 `0`。
