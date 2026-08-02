# Evals

`cases.jsonl` 保存 30 条固定合成评测合同：成功 12、歧义 5、无答案 5、越权 4、注入 4。
每条包含问题、参考 SQL 或空值，以及预期终态、审批和结果。

原 20 条案例保持不变；新增 10 条未见题按 `4/2/2/1/1` 扩充。新成功题保存可复算参考 SQL，
新歧义、无答案、越权与注入题只保存预期路由，其中新越权和无答案题不预写 SQL。

`contract.py` 严格检查数据形状，并使用现有产品工作流复算成功与越权参考 SQL。它不调用模型，
也不把参考 SQL 当作模型输出。合同测试已由 `api/tests/test_eval_contract.py` 纳入现有 CI 测试入口。

`runner.py` 逐条调用现有产品工作流，保存完整 run record/trajectory、脱敏 usage、数据集与业务库
哈希，并计算执行成功率、答案正确率和人工介入率。Provider 必须由命令行显式指定；运行器不自动
重试、不覆盖已有 checkpoint 或报告。模拟批准只用于完成评测，不代表产品自动审批。

真实 DeepSeek 运行命令形状如下；数据库、checkpoint 和报告应放在 Git 忽略的 `.local/`：

```powershell
$env:PYTHONPATH='api/src'
python -m evals.runner --provider deepseek --evaluation-id <run-id> `
  --business-database <business.sqlite3> `
  --checkpoint-database <workflow.sqlite3> `
  --output <report.json>
```

首次固定 20 条 DeepSeek 基线已完成：执行成功率 `7/8`、答案正确率 `14/20`、人工介入率
`7/20`，20 次调用合计 `19231` tokens，自动重试为 `0`。这是单次冻结合成集结果，不代表生产
可靠性；完整判定与安全回执见 [`docs/work/model-eval-runner.md`](../docs/work/model-eval-runner.md)。

训练对召回合入后的唯一复跑 `trainpair-20260802T134352Z` 使用同一 20 条冻结集且自动重试为 `0`：
执行成功率 `8/8`、答案正确率 `17/20`、人工介入率 `4/20`，20 次调用合计 `24379` tokens。
业务库哈希不变且越权执行为 `0`；完整前后对比、剩余错误和报告哈希见
[`docs/work/training-pair-frozen-eval.md`](../docs/work/training-pair-frozen-eval.md)。

三条确定性意图规则加入后的唯一复跑 `intentfix-20260802T142421Z` 得到执行成功率 `8/8`、答案
正确率 `20/20`、人工介入率 `4/20`；三条本地终止使真实 Provider 调用降为 `17`，自动重试仍为
`0`，合计 `20821` tokens。越权与非成功类别 SQL 执行均为 `0`；完整边界见
[`docs/work/intent-routing-fix.md`](../docs/work/intent-routing-fix.md)。

扩充后唯一 30 题运行 `unseen30-20260802T144417Z` 形成独立首份基线：执行成功率 `12/12`、
答案正确率 `26/30`、人工介入率 `9/30`；真实 Provider usage `27` 条、自动重试 `0`，合计
`32969` tokens。新 10 题正确 `6/10`，越权与全部非成功 SQL 执行均为 `0`，业务库哈希不变；
它不替换旧 20 题结果。完整错误与报告哈希见
[`docs/work/frozen-eval-30.md`](../docs/work/frozen-eval-30.md)。

合成枚举值索引后的唯一复跑 `enum30-20260802T151131Z` 保持执行成功率 `12/12`、答案正确率
`26/30`、人工介入率 `9/30`，30 条的判定与结果均未改变；真实 Provider usage 仍为 `27` 条，
total tokens 从 `32969` 增至 `34473`，自动重试 `0`。越权与全部非成功 SQL 执行均为 `0`，业务
库哈希不变；该轮证明不降但没有证明指标提升。完整边界见
[`docs/work/enum-value-index.md`](../docs/work/enum-value-index.md)。

把 `success-009..012` 明确作为已见开发集并补入版本化知识层后，唯一复跑
`devfix30-20260802T153713Z` 得到执行成功率 `12/12`、答案正确率 `30/30`、人工介入率 `5/30`；
真实 Provider usage `27` 条、自动重试 `0`、合计 `35050` tokens。越权与全部非成功 SQL 执行仍
为 `0`，业务库哈希不变；该结果只证明已见错误被修复，不构成新的未见或泛化证据。完整边界见
[`docs/work/unseen-success-fix.md`](../docs/work/unseen-success-fix.md)。
