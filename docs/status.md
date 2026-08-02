# 当前开发状态

> 只保存当前事实；历史证据与回执见 [`docs/status-log/`](status-log/)，稳定边界见 [`PROJECT.md`](../PROJECT.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `blocked` |
| 更新时间 | `2026-08-02` |
| 当前切片 | `TRAINING-PAIR-RETRIEVAL-024`：冻结成功案例训练对与轻量相似召回 |
| 最近完成 | `WEB-SHOWCASE-REPLAY-022`：PR #17 合并为 `03c84b6a`，main 三个 CI job 全绿 |
| 当前状态 | PR #18 的 web / container 已绿；API 因当前层测试总数措辞不匹配园丁合同而失败 |
| 完成门 | 本地一行修复全量通过；待获准推送新 head 后三 CI 全绿并 squash |
| 项目基线 | `origin/main@03c84b6a`；main CI run `30746089212` 成功 |
| 阻碍 | 本单唯一一次 push 已用；修复后的新 head 需要用户另批一次有界 push |

## 当前队列

- 已完成本地：8 条可禁用训练对，阈值 `0.72`、最多召回 2 条；Python 全量 `74` 项本地测试通过。
- 不做：向量库、embedding、工作流改造、Provider 调用或评测复跑。
- 保留：首次真实 20 条基线 `7/8`、`14/20`、`7/20`，不做 prompt 调优或补跑。

## 下一检查点

- 修复当前层措辞并重跑全部本地门，记录精确新 head 后请求一次补充 push 授权。
- 获批后只推该 head；PR #18 三 CI 全绿才 squash，不顺手启动评测复跑。
