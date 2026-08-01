# 当前开发状态

> 本文件只保存当前事实、验证证据和下一检查点。稳定边界见 `PROJECT.md`。

| 字段 | 内容 |
| --- | --- |
| `state` | `ready` |
| 更新时间 | `2026-08-01` |
| 最近完成 | `APPROVAL-GATE-004`：机械 SQL 审批分类、真实中断恢复、决定幂等与不可绕过只读边界 |
| 前序能力 | `WORKFLOW-CORE-002`：离线 LangGraph 状态机、独立 checkpoint、稳定 trajectory 与失败终态 |
| 做什么 | 高行数和写操作 SQL 在执行前持久化挂起；同一 run ID 可跨进程批准或拒绝 |
| 不做什么 | 未接 LLM、真实身份权限、自动重试、FastAPI、网页、Docker、Postgres 或完整评测 |
| 完成门 | 普通查询直通；高行数批准只执行一次；拒绝和写操作批准不执行；重复决定显式失败；业务库不变 |
| 风险 | 产品运行保持本地合成数据、无 Provider/费用；开发安装只读取公开包索引，无账号或业务写入 |
| 项目基线 | 本地与远端分支 `codex/approval-gate` 基于已合并并通过 CI 的 `origin/main@63381f9` |
| 阻碍 | 无工程阻碍；Draft PR #2 已打开且 CI 通过，尚未授权合并 |

## 复用审查

- 已复用 Traceable 的 `api/src + api/tests` 布局、稳定事实/当前状态分离、失败关闭测试思路和
  只读 GitHub Actions 权限姿态。
- Traceable 没有可直接复用的 NL2SQL 只读执行器；本切片使用 Python `sqlite3` 的 URI
  `mode=ro`、`PRAGMA query_only` 和 authorizer 组成薄适配层。
- 暂不搬运其完整发布证明、Provider 预算、部署和多工作区治理；这些不属于当前完成门。

## 验证证据

- `PYTHONPATH=api/src python -m unittest discover -s api/tests -p "test_*.py" -v`：
  `Ran 8 tests in 0.259s`，`OK`。
- `python -m compileall -q api/src`：退出码 `0`。
- CLI 冒烟：创建 `.local/cli-demo.sqlite3` 后读回
  `tables=customers,order_items,orders,products`、`orders=6`。
- 测试内固定表行数为 `4 / 5 / 6 / 11`、聚合结果为 `5946.0`；7 类越界语句被拒绝，
  随后订单数和 4 表 schema 均未变化。
- `.github/workflows/ci.yml` 已配置 Python 3.13 编译和相同单测；远端当前结论以
  [GitHub Actions](https://github.com/suuny-ab/auditable-nl2sql-agent/actions/workflows/ci.yml)
  为准，不得把本地绿色写成远端 CI 已通过。
- 首次公开推送 SHA `429b44007e7848317fcccd3199a168ff97fc8075`；GitHub Actions
  [run 30628166219](https://github.com/suuny-ab/auditable-nl2sql-agent/actions/runs/30628166219)
  在该 SHA 上完成，结论为 `success`。
- [PR #1](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/1) 已合并为 `63381f9`；
  [main CI run 30684609206](https://github.com/suuny-ab/auditable-nl2sql-agent/actions/runs/30684609206)
  在该 SHA 上完成，结论为 `success`。

## APPROVAL-GATE-004 验证证据

- SQLite `EXPLAIN QUERY PLAN` 与现有 authorizer 组成不执行结果计划的机械校验；写操作和
  `PRAGMA` 被拒绝，字符串策略只用于保守行数分类，不承担只读安全边界。
- `LIMIT 6` 在阈值 5 下挂起，第二个真实 Python 进程批准后只执行一次；拒绝、非法决定、
  缺失 run 和终态重复决定均失败关闭。
- 写 SQL 的审批状态固定 `can_execute=false`；即使批准也以
  `approval_cannot_override_read_only` 结束，执行尝试为 0，业务库哈希不变。
- 当前全量测试为 20 项本地通过；完整合同见
  [`docs/work/approval-gate.md`](work/approval-gate.md)。候选已进入
  [Draft PR #2](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/2)，当前 HEAD 的远端 CI
  结论为 `success`，PR 未获得合并授权。

## 下一候选

下一切片候选是结果校验与证据绑定：把 SQL、schema 快照、结果行和校验结论绑定为稳定证据
对象，但仍不接真实 LLM、FastAPI、网页或完整评测。

## 审批中断/恢复最小风险探针

2026-08-01 在 Git 忽略目录完成，正式产品代码和依赖未变化：

- 进程 A 将高行数只读查询持久化为 `pending_approval` 并退出；进程 B 用同一 run ID 和
  `Command(resume=...)` 恢复为 `completed`，返回 11 行且独立执行账本恰好为 `1`。
- 第三个进程重复提交相同决定时没有重复执行，但 LangGraph 是静默 no-op，不会主动拒绝；
  正式 runner 因此需要显式终态检查和决定幂等合同。
- 独立拒绝 run 得到 `rejected`，执行计数为 `0`；批准和拒绝终态均无待处理任务。
- 最终 8 项机器断言全部通过，业务库 SHA-256 始终为
  `564572c5667de341521fcf0405b1749bd240b7a7318e02bf11b8938cce491ea7`。
- 完整合同与失败修正记录见
  [`docs/work/approval-interrupt-probe.md`](work/approval-interrupt-probe.md)。

## WORKFLOW-CORE-002 验证证据

- `langgraph==1.2.9`、`langgraph-checkpoint==4.1.1`、
  `langgraph-checkpoint-sqlite==3.1.0` 及全部传递依赖已从 hash 锁文件安装到全新
  Python `3.13.12` 虚拟环境；`pip check` 为 `No broken requirements found`。
- `PYTHONPATH=api/src python -m unittest discover -s api/tests -p "test_*.py" -v`：
  `Ran 16 tests in 1.862s`，`OK`；其中 7 条为工作流定向测试、8 条为原数据库回归、
  1 条钉定 pyproject / 顶层 requirements / hash 锁一致性。
- 成功 run 得到 `completed`、`5946.0` 和 `load_schema/draft_sql/execute_sql/finish` 四条
  有序 trajectory；失败路径固定自动重试 `0`，执行尝试最多 `1`。
- 独立第二 Python 进程使用会抛错的 generator 构造 runner，仍能只读回原 run，证明
  `get_run` 不会重新执行节点；这只证明持久化回查，不证明中断恢复。
- 成功、执行错误和写操作拒绝测试均比较业务库 SHA-256；workflow 表只存在于独立状态库。
- `compileall`、空白检查、公开内容扫描通过。PR #1 已合并，`main@63381f9` 的 Python 3.13
  远端 CI 已通过。

## LangGraph 最小风险探针

2026-07-31 在 Git 忽略的临时目录中完成，不包含正式产品代码或项目依赖变更：

- 隔离 Python `3.13.12` 成功安装 `langgraph==1.2.9`、
  `langgraph-checkpoint==4.1.1`、`langgraph-checkpoint-sqlite==3.1.0`。
- 第一进程运行 `draft_sql → execute_sql → finish` 三节点图，真实调用现有只读执行器，
  `probe-run-001` 得到 `completed`、`5946.0`、5 个 checkpoint 和 3 条 JSON trajectory。
- 第二个独立 Python 进程没有执行节点，通过公开 `get_state/get_state_history` API 从独立
  workflow SQLite 读回相同 run、终态、结果和 trajectory。
- 业务库探针前、第一进程后、第二进程后的 SHA-256 均为
  `564572c5667de341521fcf0405b1749bd240b7a7318e02bf11b8938cce491ea7`；仍为 4 表、6 笔订单。
- 结论：候选依赖、Python 3.13、严格 MessagePack、独立 SQLite checkpoint 和公开 API
  trajectory 投影的核心可行性已通过；失败终态、正式依赖锁和产品结构仍须在下一切片实现。
