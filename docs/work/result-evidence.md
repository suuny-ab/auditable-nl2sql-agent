# RESULT-EVIDENCE-006

> 状态：`completed`
>
> 日期：`2026-08-01`
>
> 基线：`0e7f848c512d73ef4c9e53bd6b095a63416ec128`

## 做什么

- 在 SQL 执行后增加 `validate_result` 和 `bind_evidence` 两个 LangGraph 节点。
- 结果校验覆盖列名、行宽、截断状态和严格 JSON 标量；失败形成持久化失败终态。
- 成功结果绑定 run ID、问题、SQL、schema 快照、结果和校验回执，生成版本化 evidence。
- evidence 使用规范 JSON 与 SHA-256，并提供独立重算验证函数。
- 结果硬上限进入 run state，保证进程重启后恢复使用原始上限，而不是新进程的构造参数。
- 稳定 run record 升级并投影结果校验与 evidence。

## 不做什么

- 不接 LLM、Provider、自然语言回答或业务语义正确性判断。
- 不做数字签名、密钥、外部存证、真实身份权限、并发审批者竞争。
- 不做 FastAPI、网页、完整评测、Docker 或 Postgres。
- 不增加第三方依赖，不修改数据库只读和审批安全边界。
- 不自动重试。

## 怎样算完成

- 普通成功 run 和人工批准后的成功 run 都得到可重算的 `evidence-v1`。
- 第二个独立 Python 进程按 run ID 回查并重新验证 evidence 指纹，且不重新执行工作流节点。
- 结果被截断时得到 `failed/result_truncated`，不产生 evidence。
- 纯结果校验对行宽异常、`NaN` 和二进制值失败关闭。
- 审批拒绝、写 SQL、无效 SQL、未知问题和缺失 schema 不产生 evidence。
- trajectory 的成功路径固定包含 `validate_result` 与 `bind_evidence`；失败路径停在准确节点。
- 原有测试全部通过，新增成功和失败路径测试；业务库哈希不变。
- 编译、锁定依赖、差异和公开内容检查通过；只本地提交，不推送。

## Evidence 合同

- envelope：`schema_version`、`payload`、`fingerprint`。
- payload：run ID、问题、SQL、schema 快照、结果与校验回执。
- fingerprint：`algorithm=sha256`、`canonicalization=canonical-json-v1`、`value`。
- SHA-256 只覆盖 payload 的规范 JSON；它用于稳定绑定和意外变化检测，不是数字签名，也不证明
  SQL 或答案语义正确。

## 证据

- `WorkflowState` 持久化创建 run 时的 `result_row_limit`；执行后依次进入 `validate_result`、
  `bind_evidence`，稳定投影升级为 `run-record-v3`。
- 普通成功和第二进程审批恢复成功均产生 `evidence-v1`；第二个独立 Python 进程按 run ID
  回查后调用 `verify_evidence` 重算通过，未重新运行 graph 节点。
- 5 行硬上限下执行 `LIMIT 11` 得到 5 行且 `truncated=true`，随后以
  `failed/result_truncated` 停在结果校验节点，evidence 为 `null`；恢复 runner 的构造上限为
  100，证明执行使用的是 state 中的原始上限。
- 纯校验测试覆盖空列、行宽错误、截断、`NaN`、`bytes`；绑定测试覆盖字典顺序无关、payload
  变化检测和伪造校验回执拒绝。
- Python `3.13.12`：`python -m unittest discover -s api/tests -p "test_*.py" -v` 得到
  `Ran 25 tests`、`OK`；`compileall`、`pip check` 和 `git diff --check` 通过。
- 成功、执行错误、写操作审批拒绝和截断集成测试均在前后比较业务数据库 SHA-256，结果不变。
- 本切片未增加依赖、未调用 Provider、未推送远端；因此没有本提交的远端 CI 结论。
