# EVAL-DATASET-008

> 状态：`completed`
>
> 日期：`2026-08-01`
>
> 基线：`887f20fe3d51c19756fc0c7745e54a16f30fe446`

## 做什么

- 冻结 20 条仅使用现有合成电商 schema 的评测案例。
- 分类固定为：成功 8、歧义 3、无答案 3、越权 3、注入 3。
- 每条保存稳定 ID、类别、自然语言问题、参考 SQL 或空值、预期终态、错误码、审批预期和
  参考结果。
- 使用标准库实现严格 JSONL 合同校验，拒绝未知字段、重复 ID/问题、非法 JSON 数值和分类漂移。
- 使用现有产品工作流复算成功与越权案例：成功 SQL 必须得到固定结果；高行数案例必须进入
  可执行审批；越权 SQL 必须进入不可执行审批且批准也不能绕过只读边界。
- 将数据合同测试纳入现有 CI 测试入口。

## 不做什么

- 不调用 LLM、DeepSeek 或任何 Provider，不产生费用。
- 不实现模型评测运行器，不计算执行成功率、答案正确率或人工介入率。
- 不调提示词，不扩展 SQL generator，不把参考 SQL 当作模型输出。
- 不修改产品工作流、数据库 schema、审批策略、FastAPI、网页或 Docker。
- 不增加第三方依赖。

## 怎样算完成

- 数据集恰好 20 条，ID 和问题唯一，五类数量为 `8/3/3/3/3`。
- 成功和越权案例必须有参考 SQL；歧义、无答案和注入案例不得预写 SQL。
- 8 条成功参考 SQL 在现有只读工作流中全部得到与合同一致的列、行和截断状态。
- 其中至少 1 条安全高行数查询先挂起，批准后完成；其余直接完成。
- 3 条越权参考 SQL 全部先挂起且 `can_execute=false`，即使批准也以
  `approval_cannot_override_read_only` 结束，执行尝试为 0。
- 数据库在参考案例复算前后 SHA-256 不变。
- 非执行类别的终态、错误码和审批预期符合类别合同。
- 原有测试全部通过；编译、锁定依赖、差异和公开内容检查通过。
- 只本地提交，不推送。

## 声明边界

- 这是后续模型评测的固定输入与 gold contract，不是模型运行结果。
- 当前切片不能产生或宣传任何成功率、正确率或人工介入率数字。
- 参考 SQL 只用于验证合成数据事实与预期安全路由，不构成真实 NL2SQL 能力证明。

## 证据

- `evals/cases.jsonl` 固定 20 条案例和完整 ID 集合，分类为成功 8、歧义 3、无答案 3、越权 3、
  注入 3；每条使用同一 `eval-case-v1` 合同。
- 严格加载器拒绝空行、未知字段、重复 ID/问题、非标准 JSON 常量和分类漂移；结果继续复用产品
  `validate_result`，没有复制第二套结果合法性规则。
- 参考 SQL 通过 `StaticSqlGenerator` 注入现有 `WorkflowRunner`，不作为模型输出：8 条成功案例
  的列、行、截断状态与 gold 完全一致。
- 成功案例中 7 条直通，`success-008` 先进入可执行审批，批准后返回固定 11 行；3 条越权案例
  均进入不可执行审批，模拟批准后执行尝试仍为 0，evidence 和 answer 均为空。
- 11 条参考案例复算前后业务数据库 SHA-256 完全相同。
- Python `3.13.12`：`python -m unittest discover -s api/tests -p "test_*.py" -v` 得到
  `Ran 33 tests`、`OK`；`compileall`、`pip check`、`git diff --check` 和变更文件公开内容扫描通过。
- 本切片未调用 Provider、未计算任何指标、未增加依赖。
  [Draft PR #5](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/5) 已创建；
  [CI run 30690243508](https://github.com/suuny-ab/auditable-nl2sql-agent/actions/runs/30690243508)
  在 implementation SHA `33653d2` 上完成，结论为 `success`。
