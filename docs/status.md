# 当前开发状态

> 本文件只保存当前事实、验证证据和下一检查点。稳定边界见 `PROJECT.md`。

| 字段 | 内容 |
| --- | --- |
| `state` | `ready` |
| 更新时间 | `2026-08-01` |
| 最近完成 | `EVAL-DATASET-008`：冻结 20 条 `8/3/3/3/3` 合成 gold contract 并复算参考 SQL |
| 前序能力 | `EVIDENCE-ANSWER-007`：由完整 evidence 生成带精确来源的确定性 `answer-v1` |
| 做什么 | 固定问题、类别、参考 SQL/空值、终态、审批和结果，并机器校验 gold contract |
| 不做什么 | 未调用模型、未计算指标、未调提示词、未改工作流、FastAPI、网页或 Docker |
| 完成门 | 20 条和 ID 固定；成功/越权参考 SQL 路由与结果一致；非执行类别合同明确；业务库不变 |
| 风险 | 产品运行保持本地合成数据、无 Provider/费用；开发安装只读取公开包索引，无账号或业务写入 |
| 项目基线 | `main@01db420`：PR #5 已合并，merge commit 远端 CI 通过 |
| 阻碍 | 无工程阻碍 |

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

## RESULT-EVIDENCE-006 验证证据

- 成功路径固定经过 `execute_sql → validate_result → bind_evidence → finish`；普通 run 与跨进程
  批准后的 run 均得到可由 `verify_evidence` 重算的 `evidence-v1`。
- 第二个真实 Python 进程按 run ID 回查 checkpoint 并重算 evidence 指纹，generator 与图节点
  均未重新执行。
- 创建 run 时的结果硬上限持久化在 state；以 5 行上限创建的挂起 run，在采用默认 100 行上限
  的新 runner 中恢复后仍只返回 5 行，并以 `failed/result_truncated` 停在 `validate_result`，不产
  evidence。
- 纯校验器对空列、行宽错误、截断、`NaN` 和 `bytes` 分别失败关闭；错误 SQL、未知问题、
  缺失 schema、审批拒绝和写 SQL 批准路径均不产 evidence。
- Python `3.13.12` 全量产品测试 25 项通过，`compileall`、`pip check` 与 `git diff --check`
  通过；成功、执行失败、写操作拒绝与截断路径均校验业务数据库哈希不变。
- 完整合同与声明边界见 [`docs/work/result-evidence.md`](work/result-evidence.md)。
  [PR #3](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/3) 已合并为 `9f2b652`；
  [main CI run 30687356777](https://github.com/suuny-ab/auditable-nl2sql-agent/actions/runs/30687356777)
  在该 SHA 上完成，结论为 `success`。

## EVIDENCE-ANSWER-007 验证证据

- 成功路径固定增加 `compose_answer`：单值结果生成精确单元格引用，多行结果只陈述行数与字段，
  零行结果明确表示未返回数据。
- 回答前同时校验 evidence 指纹与完整绑定合同；指纹篡改、以及重新计算指纹但加入合同外字段的
  evidence 均失败关闭。
- 回答异常形成 `failed/evidence_verification_failed` 并停在 `compose_answer`；有效 evidence
  保留，answer 为 `null`。审批拒绝、写操作、错误 SQL、未知问题、缺失 schema 和截断路径也
  不产生 answer。
- 第二个真实 Python 进程按 run ID 回查的 answer 与原记录完全一致，且不重新执行图节点。
- Python `3.13.12` 全量产品测试 30 项通过；成功、回答失败和原安全失败路径继续验证业务库
  SHA-256 不变；`compileall`、`pip check`、差异与公开内容检查通过。完整合同见
  [`docs/work/evidence-answer.md`](work/evidence-answer.md)。
- [PR #4](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/4) 已合并为 `c85fdb5`；
  [main CI run 30688678078](https://github.com/suuny-ab/auditable-nl2sql-agent/actions/runs/30688678078)
  在该 SHA 上完成，结论为 `success`。

## EVAL-DATASET-008 验证证据

- `evals/cases.jsonl` 恰好 20 条，固定 ID 与分类为成功 8、歧义 3、无答案 3、越权 3、注入 3；
  ID 和问题均唯一。
- 严格 JSONL 校验拒绝空行、未知字段、重复 ID、非法 `NaN`、类别数量漂移和 gold 字段漂移；
  成功与越权必须带参考 SQL，其余类别禁止预写 SQL。
- 8 条成功参考 SQL 经现有工作流复算：7 条直接完成，1 条 `LIMIT 11` 安全查询先挂起、批准后
  完成；列、行和截断状态全部与 gold 一致。
- 3 条越权参考 SQL 均先挂起且 `can_execute=false`，模拟批准后仍以
  `approval_cannot_override_read_only` 结束，执行尝试为 0，不产生 evidence 或 answer。
- 11 条参考案例复算前后业务数据库 SHA-256 不变；合同测试已进入现有 `api/tests` CI 入口。
- Python `3.13.12` 全量产品与合同测试 33 项通过；`compileall`、`pip check`、差异与公开内容
  检查通过。
- 当前数据集不是模型运行结果，尚无执行成功率、答案正确率或人工介入率。完整合同见
  [`docs/work/eval-dataset.md`](work/eval-dataset.md)。
- [PR #5](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/5) 已合并为 `01db420`；
  [main CI run 30690523646](https://github.com/suuny-ab/auditable-nl2sql-agent/actions/runs/30690523646)
  在该 SHA 上完成，结论为 `success`。

## APPROVAL-GATE-004 验证证据

- SQLite `EXPLAIN QUERY PLAN` 与现有 authorizer 组成不执行结果计划的机械校验；写操作和
  `PRAGMA` 被拒绝，字符串策略只用于保守行数分类，不承担只读安全边界。
- `LIMIT 6` 在阈值 5 下挂起，第二个真实 Python 进程批准后只执行一次；拒绝、非法决定、
  缺失 run 和终态重复决定均失败关闭。
- 写 SQL 的审批状态固定 `can_execute=false`；即使批准也以
  `approval_cannot_override_read_only` 结束，执行尝试为 0，业务库哈希不变。
- 当前全量测试为 20 项本地通过；完整合同见
  [`docs/work/approval-gate.md`](work/approval-gate.md)。[PR #2](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/2)
  已合并为 `d7be385`；
  [main CI run 30685924831](https://github.com/suuny-ab/auditable-nl2sql-agent/actions/runs/30685924831)
  在该 SHA 上完成，结论为 `success`。

## EVIDENCE-FINGERPRINT-PROBE-005 验证证据

- 两个独立 Python 进程对不同字典插入顺序的同一 evidence 得到相同的 2932 字节规范 JSON 和
  SHA-256 `b5522364…60dc`。
- SQL、schema、结果三类单字段变化全部产生不同指纹；截断、行宽错误、`NaN`、`bytes` 四类
  非法输入全部拒绝。
- 最终 7 项机器断言全部通过，业务库 SHA-256 始终为 `564572c5…1ea7`；未修改产品代码或依赖。
- 完整合同、指纹和声明边界见
  [`docs/work/evidence-fingerprint-probe.md`](work/evidence-fingerprint-probe.md)。

## 下一候选

下一步候选是 DeepSeek 最小 Provider 探针：仅在 Git 忽略目录验证凭据、兼容接口、结构化 SQL
输出与少量固定案例，不修改产品代码。该动作会产生外部调用和费用，必须另获当次授权。

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
