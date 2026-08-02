# Evals

`cases.jsonl` 保存 40 条固定合成评测合同：成功 16、歧义 7、无答案 7、越权 5、注入 5。
每条包含问题、参考 SQL 或空值，以及预期终态、审批和结果。

前 30 条案例保持不变；本轮再按 `4/2/2/1/1` 增加 10 条高难未见题。新成功题覆盖多表关联、
易混价格口径、边界数值和组内 Top 1，并保存可复算 reference SQL；新歧义、无答案、越权与注入
题只保存预期路由，不预写 SQL。逐题难度边界见
[`docs/work/frozen-eval-40.md`](../docs/work/frozen-eval-40.md)。

`contract.py` 严格检查数据形状，并使用现有产品工作流复算成功与越权参考 SQL。它不调用模型，
也不把参考 SQL 当作模型输出。合同测试已由 `api/tests/test_eval_contract.py` 纳入现有 CI 测试入口。

`runner.py` 逐条调用现有产品工作流，保存完整 run record/trajectory、脱敏 usage、数据集与业务库
哈希，并计算执行成功率、答案正确率和人工介入率。Provider 必须由命令行显式指定；运行器不自动
重试、不覆盖已有 checkpoint 或报告。模拟批准只用于完成评测，不代表产品自动审批。

`schema_holdout.py` 与 `schema_holdout_cases.jsonl` 是独立的换 schema 泛化考场：三张新表把订单头
并入交易行事实，金额改为整数分，状态 / 渠道改码，且表名、字段名与主库零重合。15 个问题与主库
来源题逐字相同，reference SQL 只按新 schema 重写；合同固定 `7/2/2/2/2` 类别和来源 ID。它不进入
训练对，也不替换原 40 题合同。

`paraphrase_cases.json` 是独立的同义改述考场：从主库 40 题中按五类各选 2 题，每题保存
`formal / colloquial / restructured` 三种自然问法，共 30 条。文件显式声明含义不变并映射来源题；
`paraphrase.py` 把来源题的类别、reference SQL 和 expected 原样投影到改述题，严格拒绝来源漂移，
同时把每条结果与封存的原题判定比较为稳定、掉分或改善。它不修改主 40 题、知识层或训练对。

真实 DeepSeek 运行命令形状如下；数据库、checkpoint 和报告应放在 Git 忽略的 `.local/`：

```powershell
$env:PYTHONPATH='api/src'
python -m evals.runner --provider deepseek --evaluation-id <run-id> `
  --business-database <business.sqlite3> `
  --checkpoint-database <workflow.sqlite3> `
  --output <report.json>
```

换 schema HOLDOUT 必须显式创建新 fixture 并选择独立合同；省略 `--dataset-contract` 会继续按原 40 题
失败关闭：

```powershell
$env:PYTHONPATH='api/src'
python -m evals.schema_holdout --output <schema-holdout.sqlite3>
python -m evals.runner --provider deepseek --evaluation-id <run-id> `
  --dataset evals/schema_holdout_cases.jsonl `
  --dataset-contract schema-holdout-v1 `
  --business-database <schema-holdout.sqlite3> `
  --checkpoint-database <workflow.sqlite3> `
  --output <report.json>
```

HOLDOUT 的 schema、数据、映射题和 gold 必须在真实调用前冻结；首次完整运行无论高低即为最终基线，
不得据结果调优或补跑。完整停止线见
[`docs/work/schema-holdout.md`](../docs/work/schema-holdout.md)。

同义改述评测也必须显式选择独立合同；30 个变体最多各进入 Provider 一次，运行器自动重试仍为 `0`：

```powershell
$env:PYTHONPATH='api/src'
python -m evals.runner --provider deepseek --evaluation-id <run-id> `
  --dataset evals/paraphrase_cases.json --dataset-contract paraphrase-v1 `
  --business-database <business.sqlite3> `
  --checkpoint-database <workflow.sqlite3> `
  --output <report.json>
```

销售额同义词修复后的定向复测复用同一冻结文件，但合同只放行上一轮掉分的
`ambiguity-001-p1..p3`；它不重跑或重写其余 27 题：

```powershell
$env:PYTHONPATH='api/src'
python -m evals.runner --provider deepseek --evaluation-id <run-id> `
  --dataset evals/paraphrase_cases.json --dataset-contract paraphrase-revenue-v1 `
  --business-database <business.sqlite3> `
  --checkpoint-database <workflow.sqlite3> `
  --output <report.json>
```

唯一轮次 `revenuepara3-20260802T181238Z` 将所选三题从 `0/3` 修复到 `3/3`，投影完整改述
`24/30 → 27/30`。三题都由本地意图门澄清，真实 Provider 调用 / usage / token 与 SQL 执行均为
`0`，自动重试 `0`，业务库不变；零 success 子集的执行成功率以 `0/0, value=null` 表示不可适用。
完整的只读报告恢复边界与哈希见
[`docs/work/paraphrase-synonym-coverage.md`](../docs/work/paraphrase-synonym-coverage.md)。

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

前 30 条保持不变并再新增 10 条高难题后，唯一轮次 `unseen40-20260802T155929Z` 形成独立 40 题
基线：执行成功率 `14/16`、答案正确率 `32/40`、人工介入率 `10/40`；37 条进入 Provider
transport，35 条保存 usage，自动重试 `0`，合计 `45620` tokens。两条旧成功题 transport 失败；
新增 10 题正确 `4/10`。越权与全部非成功 SQL 执行均为 `0`，业务库哈希不变；本轮不补跑、不修
题，与开发集 `30/30` 分开保存。完整边界见
[`docs/work/frozen-eval-40.md`](../docs/work/frozen-eval-40.md)。

第二合成 schema 的首次且唯一 HOLDOUT `schema15-20260802T165212Z` 对 15 个主库同题各调用一次，
主库同题 → 换 schema 为执行成功率 `7/7 → 0/7`、答案正确率 `15/15 → 6/15`、人工介入率
`2/15 → 2/15`；15 条 usage 合计 `17433` tokens，自动重试 `0`。7 条成功与 2 条歧义均保守判为
`no_answer`，所有 SQL 执行和越权执行均为 `0`，业务库哈希不变。该首个数字按 HOLDOUT 纪律封存，
证明当前 schema 泛化不足；不据此修改考场或补跑。完整证据见
[`docs/work/schema-holdout.md`](../docs/work/schema-holdout.md)。

规则式 schema 知识自动构建接入后的唯一复测 `autoknowledge15-20260802T172429Z` 使用同一 LF 冻结
HOLDOUT，执行成功率 `0/7 → 3/7`、答案正确率 `6/15 → 8/15`、人工介入率
`2/15 → 5/15`；15 条 usage 的 total tokens 为 `20911`，自动重试 `0`。两条歧义题恢复正确澄清，
但成功题仍为 `0/7`；三条成功 SQL 虽只读执行，仍因状态码、金额单位 / 结果和审批不符而判错。越权
与全部非成功 SQL 执行为 `0`，业务库哈希不变；结果只证明局部路由改善，不代表 schema 泛化成功。
完整证据见 [`docs/work/schema-knowledge-builder.md`](../docs/work/schema-knowledge-builder.md)。

通用紧凑 schema 摘要接入后的唯一复测 `schemasummary15-20260802T184047Z` 仍使用同一冻结
HOLDOUT：执行成功率 `3/7 → 2/7`、答案正确率 `8/15 → 8/15`、人工介入率 `5/15 → 4/15`，
成功类仍 `0/7`。15 条 usage 合计 `25292` tokens、自动重试 `0`；越权与全部非成功 SQL 执行
均为 `0`，业务库不变。该结果表明只压缩结构表示不足以解决未知枚举与输出合同问题，不补跑或调题；
完整边界见 [`docs/work/schema-summary-injection.md`](../docs/work/schema-summary-injection.md)。

主库 10 个来源题的唯一同义改述基线 `paraphrase30-20260802T174944Z` 对每题固定 3 种问法：来源
原题正确 `8/10`，改述正确 `24/30`；逐变体与来源结果一致 `24/30`，完整稳定来源 `8/10`。
`ambiguity-001` 三种改述全部掉分并误执行只读 query，`ambiguity-006` 三种改述全部从原题错误改善；
二者在聚合正确率中互相抵消。26 条真实 usage 合计 `32466` tokens，另 4 条本地终止，自动重试 `0`、
transport 失败 `0`；越权执行为 `0`、业务库不变。完整边界见
[`docs/work/paraphrase-eval.md`](../docs/work/paraphrase-eval.md)。
