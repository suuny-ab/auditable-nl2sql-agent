# 当前开发状态

> 只保存当前事实；历史证据与回执见 [`docs/status-log/`](status-log/)，稳定边界见 [`PROJECT.md`](../PROJECT.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `in-progress` |
| 更新时间 | `2026-08-03` |
| 当前切片 | `PARAPHRASE-SYNONYM-COVERAGE-035`：销售额同义词覆盖与三题唯一复测 |
| 最近完成 | `PARAPHRASE-EVAL-034`：PR #28 合并为 `b70dbb4f`，main 三个 CI job 全绿 |
| 当前状态 | 根因修复与冻结前完整本地门全绿；待提交候选后启动三题唯一复测 |
| 完成门 | 冻结候选后只复测三条掉分题；投影 24/30 前后如实落盘，三路 CI 绿后 squash 并复核 main |
| 项目基线 | `origin/main@b70dbb4f5e44206c884f21678cfff188d5c3cc4a`；main CI run `30759926736` 成功 |
| 阻碍 | 无；本单 Provider 授权尚未消费，自动重试固定 `0`，不补跑、不调题 |

## 当前队列

- 上一轮 `ambiguity-001-p1..p3` 都绕过本地意图门并错误 query；p1 / p3 已有“收入 / 销售额”命中，
  但句式包装未清空，p2 的“卖了多少钱”没有旧业务别名命中。
- “销售额”知识条目新增 `销售收入 / 销售总额 / 成交额 / 卖了多少钱`；既有意图规则只扩相同词项与
  `请 / 给出 / 我想 / 知道 / 一共 / 总额` 填充词；策略版本升为 `intent-policy-v3`，判断分支、
  action、reason 和 rule ID 未改。
- 三条冻结掉分题与两个邻近表达全部确定性澄清；业务上下文对四个新增别名全部命中。主库 16 条
  成功题与 4 条带范围的同义问题继续 Provider 路由，未被误拦。
- 定向意图 / 知识 / 改述合同 / 运行器共 `35/35`；全量 114 项测试通过，Python 为 `3.13.12`。
  Web `2/2`、编译、44 条锁依赖、strict JSON、园丁、治理与差异门全绿。
- 完整 Compose 验收确认 `10001:10001`、health `read_only=true`、固定 run 完成、POST 为 `405`，
  业务库 / checkpoint 哈希不变；容器已移除，入口脚本恢复原字节且代码 diff 为零。
- 定向复测合同只从原冻结题集选择 `ambiguity-001-p1..p3`，其余 27 题、训练对、Provider、工作流、
  只读边界与依赖不变；凭据模式与产品反向导入 `evals` 无命中。复测基线固定为所选 `0/3`、
  完整改述 `24/30`，本阶段真实 Provider 调用、usage、token 与费用为 `0`。

## 下一检查点

- 提交冻结候选；新建唯一 business / checkpoint / report 路径，只运行三题一次并落盘前后数字。
- 按本单授权推送结果 head、创建 Draft PR；三路 CI 全绿后 squash 合并并复核 main。
