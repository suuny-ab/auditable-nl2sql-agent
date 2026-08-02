# SHOWCASE-V2-FACT-SYNC-042：展示页 v2 公开事实同步

## Goal

从 `main@e7686bbae6e2ebff6d0be0510a7802d1dae2fba7` 建立只包含公开事实同步的候选：保留
结构摘要轮 `8/15、成功 0/7` 的历史位置，同时把 SQLite 原生注释轮的 `9/15、成功 1/7` 与
低基数字段值采集后的持平结果同步到 v2 页面、SSR 合同、Web 说明、数字卡和当前状态；三路 CI
全绿后 squash 合并，并停在独立部署授权门前。

## Non-goals

- 不部署、不改服务器 / Caddy / 路由 / 线上文件，不创建或发布 Sites 项目或版本。
- 不修改产品 API、workflow、安全层、Provider、数据、知识生成器、题集、评测器、依赖或 CI。
- 不运行 Provider、冻结评测、HOLDOUT、改述或任何新指标计算；token、费用与外部运行时写入为 `0`。
- 不重做视觉、交互、OG、表单、fetch、埋点或路由；`PROJECT.md` 已准确，不为凑文件修改。

## 验收标准

1. **WHEN** 开工，**THEN** remote main 仍为 `e7686bb`、无 open PR、main 三路 CI 全绿；公网仍为
   健康 v1，固定 run 为 `completed / 5946.0 / 8 节点`。
2. **WHEN** 页面陈述换库历程，**THEN** 明确区分结构摘要 `8/15、0/7`、原生注释
   `8/15 → 9/15、0/7 → 1/7` 和有限字段值采集 `9/15、1/7` 持平。
3. **WHEN** 页面解释剩余缺口，**THEN** 聚焦金额单位、输出列 / 行合同与有界查询 / 审批合同；不得
   把同一第二库集合的复测称为新 unseen 或生产泛化证据。
4. **WHEN** 检查证据链接，**THEN** 历史摘要、原生注释和值采集分别链接对应 `docs/work` 报告与
   PR #30 / #34 / #35；不得链接本机 `.local` 报告。
5. **WHEN** 运行本地门，**THEN** Web lint / build / SSR、最快相关 Python、园丁 / 治理、strict
   JSON、凭据 / 反向依赖 / diff 范围全绿，且禁改产品 / 评测 / 数据 / 部署 / 依赖 diff 为 `0`。
6. **WHEN** 远端三路检查全绿，**THEN** squash 合并并复核 main；公网仍必须是健康 v1，不部署。

## 回滚

push 前丢弃隔离 worktree / 分支；PR 未合并时关闭或保留 Draft；合并后如公开事实有误，只报告并等待
新的精确 revert 任务。本片没有运行时变更，不使用服务器或下线页面作为回滚手段。

## 规则复述

- 写入只发生在隔离 worktree；原工作区 `codex/dispatch-receipt-rule@16cbf16` 与用户 `AGENTS.md`
  修改原样保留。
- 源码合并不等于 v2 已上线；本片不调用 `sites-hosting`，不创建 / 保存 Sites version，不部署。
- Provider、新评测、服务器、Sites 外部动作与范围外写入均为 `0`；完成合并即停，不领取后续切片。

## 基线

- `origin/main@e7686bbae6e2ebff6d0be0510a7802d1dae2fba7`，main CI run `30767171976`
  的 api / web / container 全绿，无 open PR；派发单 SHA-256 为 `FF982647…284961`。
- 公网 `/nl2sql/` 返回 v1 标题且无验证弧线；health 为 `ok / read_only=true`；固定 run 为
  `completed / 5946.0 / 8 节点 / evidence-v1`。
- OG 只含主库开发弧线 `14/20 → 17/20 → 20/20 → 30/30 → 40/40` 与
  `DEV SET ≠ GENERALIZATION`，不含过期换库数字，因此原样保留。
