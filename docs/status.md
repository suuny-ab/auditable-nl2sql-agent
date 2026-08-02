# 当前开发状态

> 只保存当前事实；历史证据与回执见 [`docs/status-log/`](status-log/)，稳定边界见 [`PROJECT.md`](../PROJECT.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `in-progress` |
| 更新时间 | `2026-08-03` |
| 当前切片 | `PARAPHRASE-EVAL-034`：主库 10 题 × 3 种同义改述的唯一真实基线 |
| 最近完成 | `SCHEMA-KNOWLEDGE-BUILDER-033`：PR #27 已 squash 合并为 `e75c60e6`，main 三个 CI job 全绿 |
| 当前状态 | 30 条改述合同及完整本地门全绿；待冻结候选后启动唯一真实评测 |
| 完成门 | 冻结候选后唯一运行 ≤30 次 Provider；稳定率、掉分和 usage 落盘，三路 CI 绿后 squash 并复核 main |
| 项目基线 | `origin/main@e75c60e6f0b3a3bd22a88b8a2a4f561d721d85e9`；main CI run `30758986958` 成功 |
| 阻碍 | 无；本单 Provider 授权尚未消费，自动重试固定 `0`，不补跑、不调优 |

## 当前队列

- 改述来源按成功、歧义、无答案、越权、注入各 2 题选取；10 道原题在封存 40 题基线中正确
  `8/10`，同时包含两道原题错误，避免只测试已答对样本。
- 每个来源题固定 `formal / colloquial / restructured` 三种问法，逐条显式声明含义不变；30 个
  case ID 与问题唯一，类别为 `6/6/6/6/6`。
- 改述物化只复制来源题的类别、reference SQL 和 expected；主 40 题 LF 规范化 SHA-256 保持
  `dca2a3a0…c6a794`，知识层、训练对、意图、Provider 和工作流未改。
- 改述合同、来源漂移拒绝、只读 reference 复算和稳定率汇总共 `4/4`；全量 110 项测试通过；
  Python `3.13.12`、Web `2/2`、编译、44 条锁依赖、strict JSON、园丁、治理与差异门全绿。
- 完整 Compose 验收确认 `10001:10001`、health `read_only=true`、固定 run 完成、POST 为 `405`，
  业务库 / checkpoint 哈希不变；验证后容器已移除，入口脚本恢复原字节且代码 diff 为零。
- 知识 JSON、训练对、意图、Provider、工作流、产品依赖、主 40 题、HOLDOUT、Web 与 Compose 合同
  相对 `origin/main` 零差异；凭据模式与产品反向导入 `evals` 均无命中。
- 截至当前真实 Provider 调用、usage、token 与费用均为 `0`；唯一轮次启动前只剩候选提交与新路径
  不存在 / 凭据存在预检。

## 下一检查点

- 提交冻结候选；新建唯一 business / checkpoint / report 路径并验证预先不存在。
- 只运行一次 30 条改述评测，生成原题 `8/10` 与变体正确率、稳定率、掉分 / 改善和 usage 对比。
- 结果落盘后按本单授权推送精确 head、创建 Draft PR；三路 CI 全绿后 squash 合并并复核 main。
