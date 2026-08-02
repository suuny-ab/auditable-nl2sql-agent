# Evals

`cases.jsonl` 保存 20 条固定合成评测合同：成功 8、歧义 3、无答案 3、越权 3、注入 3。
每条包含问题、参考 SQL 或空值，以及预期终态、审批和结果。

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
