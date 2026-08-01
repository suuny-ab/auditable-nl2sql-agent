# EVIDENCE-ANSWER-007

> 状态：`completed`
>
> 日期：`2026-08-01`
>
> 基线：`038fb2d9a68c46f5b11e4ed421ec94c61030a747`

## 做什么

- 在 `bind_evidence` 后增加确定性的 `compose_answer` LangGraph 节点。
- 生成版本化 `answer-v1`，包含回答文本、evidence 指纹和精确结果引用。
- 回答前重新验证 evidence 指纹和绑定合同；校验失败时形成持久化失败终态。
- 单行结果呈现字段和值；零行和多行结果使用不超出 evidence 的保守摘要。
- 稳定 run record 投影 answer，并保证独立进程按 run ID 回查完全一致。

## 不做什么

- 不接 LLM、Provider、提示词或自然语言语义判断。
- 不声称 SQL、字段命名或回答具备业务语义正确性。
- 不扩展问题映射、schema、审批策略、结果校验或 evidence 合同。
- 不做 FastAPI、网页、评测集、Docker 或 Postgres。
- 不增加第三方依赖，不自动重试。

## 怎样算完成

- 单值成功 run 得到稳定 `answer-v1`，回答引用精确到结果单元格。
- 审批后的多行成功 run 得到行数和字段摘要，引用 evidence 中对应元数据。
- 零行结果得到“未返回数据”的保守回答，不虚构事实。
- evidence 指纹被修改或绑定内容不符合合同时，回答生成失败关闭且不返回 answer。
- 审批拒绝、写 SQL、无效 SQL、未知问题、缺失 schema 和截断结果均不产生 answer。
- 成功 trajectory 固定包含 `compose_answer`；失败停在准确节点。
- 第二个独立 Python 进程可按 run ID 读回相同 answer，且不重新执行工作流节点。
- 原有测试全部通过，新增纯函数和工作流测试；业务数据库哈希不变。
- 编译、锁定依赖、差异和公开内容检查通过；只本地提交，不推送。

## Answer 合同

- `schema_version=answer-v1`。
- `text` 只陈述 evidence 直接支持的结果，不补充解释或业务判断。
- `source` 保存 `evidence_schema_version`、`evidence_fingerprint` 和 `references`。
- 单行引用使用行号、字段名和 `payload.result.rows` 的精确路径；多行和零行摘要引用
  `returned_row_count` 与 `columns` 元数据路径。

## 证据

- 新增纯 `compose_answer`：先重算 evidence 指纹，再使用同一 payload 重新执行绑定合同；两者
  任一失败均不生成回答。
- `answer-v1` 的单行回答引用 `payload.result.rows[row][column]` 精确单元格；零行和多行不陈述
  行值，只引用 `returned_row_count` 与 `columns` 元数据。
- 工作流新增 `compose_answer` 节点，稳定投影升级为 `run-record-v4`；回答失败形成持久化终态，
  不影响已有 evidence，也不重试 SQL。
- 纯函数测试覆盖单值、零行、多行、指纹篡改，以及重新计算指纹但违反绑定合同的 evidence。
- 集成测试覆盖普通成功、跨进程审批后的多行成功、零行、回答失败和既有全部失败路径；第二个
  独立 Python 进程读回的 answer 与原记录完全相同。
- Python `3.13.12`：`python -m unittest discover -s api/tests -p "test_*.py" -v` 得到
  `Ran 30 tests`、`OK`；成功和回答失败路径均验证业务数据库 SHA-256 不变。
- `compileall`、`pip check`、`git diff --check` 和变更文件公开内容扫描通过。
- 本切片未增加依赖、未调用 Provider。[Draft PR #4](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/4)
  已创建；[CI run 30688221877](https://github.com/suuny-ab/auditable-nl2sql-agent/actions/runs/30688221877)
  在 implementation SHA `0824ac8` 上完成，结论为 `success`。
