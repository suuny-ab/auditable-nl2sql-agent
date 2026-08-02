# 当前开发状态

> 只保存当前事实；历史证据与回执见 [`docs/status-log/`](status-log/)，稳定边界见 [`PROJECT.md`](../PROJECT.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `in-progress` |
| 更新时间 | `2026-08-03` |
| 当前切片 | `SCHEMA-SUMMARY-INJECTION-036`：通用紧凑 schema 摘要注入与第二库唯一复测 |
| 最近完成 | `PARAPHRASE-SYNONYM-COVERAGE-035`：PR #29 squash 为 `1e9756e`，main 三个 CI job 全绿 |
| 当前状态 | 通用摘要与完整本地门全绿；待提交冻结候选后运行第二库 15 题唯一复测 |
| 完成门 | 两库与主库离线门全绿后冻结候选；第二库 15 题唯一复测如实落盘，三路 CI 绿后 squash 并复核 main |
| 项目基线 | `origin/main@1e9756e7e76e6388c1e0c415efe24c4f955ee4f1`；main CI run `30760925814` 成功 |
| 阻碍 | 无；本单真实复测授权未消费，最多 15 次、自动重试 `0`、不补跑 |

## 当前队列

- Provider 请求已包含完整原始 schema；本片增加的是稳定、紧凑的结构投影，不能表述为此前完全未
  提供 schema，也不以摘要猜测状态码或渠道码。
- 对比基线固定为自动知识轮次的执行 `3/7`、正确 `8/15`、介入 `5/15`；其中成功类仍 `0/7`，
  本单重点如实记录成功类前后变化。
- 主 40 题、第二库 15 题、第二库 fixture、训练对、知识 JSON、Provider 响应合同、workflow 与
  安全边界冻结；本阶段真实 Provider 调用、usage、token 与费用仍为 `0`。
- 摘要模块与 Provider 两库注入已实现，相关 Provider / 自动知识 / HOLDOUT / 主 40 离线合同
  `44/44`、Python `3.13.12` 全量 `120` 项测试、Web `2/2` 通过。
- 编译、44 条锁依赖、strict JSON、园丁、治理、Compose config、凭据 / 反向导入和差异门全绿；
  完整 Compose 验收确认 `10001:10001`、health 只读、固定 run 完成、POST `405`、两库哈希不变。
- 容器验收后已移除容器并把 CRLF 入口脚本恢复到原 SHA-256 `1c75b8d2…7d95a3a`，代码差异为零。

## 下一检查点

- 提交冻结候选，创建唯一 business / checkpoint / report 路径，只运行第二库 15 题一次。
- 无论升降均关闭复测授权、如实落盘并进入预授权远端流程。
