# APPROVAL-INTERRUPT-PROBE-003

> 状态：`completed`
>
> 日期：`2026-08-01`

## 做什么

- 在 Git 忽略目录运行一个最小 LangGraph 探针。
- 进程 A 把高行数只读查询持久化为中断状态后退出。
- 进程 B 使用同一 run ID 和 SQLite checkpoint 批准并恢复。
- 独立进程再次提交决定，验证不会重复执行查询。
- 另一个 run 覆盖人工拒绝路径。
- 比较合成业务库 SHA-256，并用独立探针账本统计执行次数。

## 不做什么

- 不修改正式 workflow、数据库执行器或产品依赖。
- 不实现审批策略、FastAPI、网页、真实身份认证或 LLM。
- 不提交探针脚本、虚拟环境、SQLite 文件或运行产物。
- 不推送 GitHub。

## 怎样算完成

- 首个进程退出后，checkpoint 显示 `pending_approval` 且存在 interrupt。
- 第二个进程批准后，同一 run 变为 `completed`，只读查询实际执行一次。
- 重复恢复不能使探针账本增加到 2。
- 拒绝 run 变为 `rejected`，且探针账本不增加。
- 所有阶段前后业务库 SHA-256 相同。
- Git 只出现本探针合同和完成后的状态记录，不出现产品代码或运行产物。

## 证据

- 锁定环境为 Python `3.13.12`、`langgraph==1.2.9`、
  `langgraph-checkpoint-sqlite==3.1.0`，未安装新依赖。
- 进程 A 创建 `interrupt-approve-001` 后退出；持久化状态为
  `pending_approval`，`next=["approval_gate"]`，interrupt 载荷包含 SQL、阈值和预计 11 行，
  执行账本为 `0`。
- 新进程批准同一 run 后得到 `completed`、返回 11 行，状态执行计数和独立账本均为 `1`。
- 第三个进程重复提交相同决定时，LangGraph 静默接受但不再执行：trajectory 不变、账本仍为
  `1`。正式 runner 必须显式拒绝已终结 run 的重复决定，不能依赖框架默认行为表达失败关闭。
- `interrupt-reject-001` 在另两个独立进程中完成挂起和拒绝；终态为 `rejected`，状态执行计数
  为 `0`，总账本仍只有批准 run 的一条记录。
- 最终机器核验的 8 项断言全部为 `true`：批准完成且只执行一次、批准/拒绝均无待处理任务、
  拒绝从未执行、账本仅含批准 run、业务数据库未变化。
- 各阶段业务库 SHA-256 均为
  `564572c5667de341521fcf0405b1749bd240b7a7318e02bf11b8938cce491ea7`。
- 首次探针 SQL 错用了不存在的 `order_item_id`，批准恢复后在只读执行器处得到明确
  `QueryExecutionError`；读取真实 schema 后改用 `order_id/product_id`，并在全新 `v2` 目录重跑
  完整链路。失败运行的执行账本为 `0`，没有业务库修改。

## 结论

真正的 SQLite checkpoint 跨进程中断/恢复可行，正式审批切片无需更换依赖或 checkpoint
方案。实现时必须在产品边界增加终态检查和决定幂等合同，并保持批准不能绕过只读执行器。
