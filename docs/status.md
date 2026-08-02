# 当前开发状态

> 只保存当前事实；历史证据与回执见 [`docs/status-log/`](status-log/)，稳定边界见 [`PROJECT.md`](../PROJECT.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `in-progress` |
| 更新时间 | `2026-08-03` |
| 当前切片 | `SHOWCASE-V2-FACT-SYNC-042`：展示页 v2 公开事实同步，停在部署门前 |
| 最近完成 | `VALUE-COLLECTION-041`：PR #35 squash 为 `e7686bb`，main 三个 CI job 全绿 |
| 当前状态 | v2 源码事实已同步；公开运行时仍是健康 v1，下一红灯是独立部署授权 |
| 完成门 | 页面 / SSR / Web 说明 / 数字卡 / 状态一致，三路 CI 后 squash；公网 v1 与 API 健康不变 |
| 项目基线 | `origin/main@e7686bbae6e2ebff6d0be0510a7802d1dae2fba7`；main CI run `30767171976` 成功 |
| 阻碍 | 无；本片不部署、不调用 Provider、不运行评测、不触碰服务器或 Sites 发布 |

## 当前事实

- 主库已见开发弧线仍为 `14/20 → 17/20 → 20/20 → 30/30 → 40/40`，不冒充未见泛化。
- 换 schema 的结构摘要历史轮为 `8/15、成功 0/7`；原生注释提升到 `9/15、成功 1/7`；有限
  字段值采集随后保持 `9/15、1/7`，没有新增提升。三轮均是同一第二库集合的开发复测。
- 剩余成功题 `6/7` 的已知缺口为金额单位、输出列 / 行合同与有界查询 / 审批合同。
- 公开 `https://47.84.34.86/nl2sql/` 仍为无验证弧线的 v1；health 为 `ok/read_only=true`，固定
  `container-demo-run` 为 `completed / 5946.0 / 8 节点`。源码合并不等于部署。
- Python 全量 `136` 项本地测试和 Web SSR `3/3` 是当前机器规模；本切片不新增测试数量或评测数字。

## 下一检查点

- 跑本地 Web / 文档 / 范围门，推送 Draft PR；api / web / container 全绿后 squash 并复核 main。
- 合并后停止。v2 部署、服务器 / Caddy / Sites 发布须新的独立当次授权。
