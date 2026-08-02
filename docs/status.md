# 当前开发状态

> 只保存当前事实；历史证据与回执见 [`docs/status-log/`](status-log/)，稳定边界见 [`PROJECT.md`](../PROJECT.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `in-progress` |
| 更新时间 | `2026-08-02` |
| 当前切片 | `TRAINING-PAIR-RETRIEVAL-024`：冻结成功案例训练对与轻量相似召回 |
| 最近完成 | `WEB-SHOWCASE-REPLAY-022`：PR #17 合并为 `03c84b6a`，main 三个 CI job 全绿 |
| 当前状态 | 8 条训练对与召回已实现；Python 全量 `74` 项、Web 构建 / SSR 2 项及全部本地门通过 |
| 完成门 | 训练对合同、命中 / 未命中 / 禁用测试与全量门通过；精确 head 三 CI 绿后 squash |
| 项目基线 | `origin/main@03c84b6a`；main CI run `30746089212` 成功 |
| 阻碍 | 无；候选待本单唯一一次 push、Draft PR 与精确 head 三 CI |

## 当前队列

- 已完成本地：8 条可禁用训练对，阈值 `0.72`、最多召回 2 条，三条定向路径全绿。
- 不做：向量库、embedding、工作流改造、Provider 调用或评测复跑。
- 保留：首次真实 20 条基线 `7/8`、`14/20`、`7/20`，不做 prompt 调优或补跑。

## 下一检查点

- 只推送最终精确候选一次并创建 Draft PR；三 CI 任一不绿则不合并。
- 远端全绿后 squash，复核 main CI 并写两层最终回执；不顺手启动评测复跑。
