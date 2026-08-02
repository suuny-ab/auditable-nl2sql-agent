# SHOWCASE-VALIDATION-ARC-037 切片合同

## Goal

把静态展示页升级为面试可读的验证叙事：用五步调优弧线、三维泛化对照和公开短板 / 改道说明，
让每个数字都能回指版本化报告回执与对应 PR，同时保留真实 run 回放和能力边界。

## Non-goals

- 不修改产品 API、workflow、Provider、知识、训练对、评测器、题集、数据、部署或公开运行时。
- 不运行新评测、不调用 Provider，不把同一开发集复跑写成未见泛化，不把投影写成完整重跑。
- 不增加现场问答、表单、客户端状态、写接口、分析埋点、依赖或新路由。
- 不部署；页面托管必须等用户明早另行批准。

## Acceptance criteria

1. **WHEN** 打开验证弧线，**THEN** 固定显示 `14/20 → 17/20 → 20/20 → 30/30 → 40/40`
   五个里程碑，顺序、数据集边界和变更类型均与版本化回执一致。
2. **WHEN** 查看任一里程碑，**THEN** 都提供一个公开报告回执链接和一个对应 PR 链接；不得链接本机
   `.local` 报告或声称 Git 忽略文件可公网读取。
3. **WHEN** 阅读调优弧线边界，**THEN** 明确前三步复用同一 20 题开发集，`30/30` 和 `40/40`
   都是在观察错误后修复的已见开发集成绩，不是独立未见泛化。
4. **WHEN** 查看泛化三维，**THEN** 分别显示主库已见开发集 `40/40`、换 schema `8/15`、同义改述
   投影 `27/30`，每项同时有报告回执和 PR 链接。
5. **WHEN** 阅读三维解释，**THEN** 明确换 schema 的成功题仍 `0/7`，`27/30` 只复跑三条掉分题并
   投影到旧基线，不能写成完整 30 题新轮次。
6. **WHEN** 阅读短板与改道，**THEN** 明示结构摘要未使 `0/7` 提升、未知值语义与输出 / 审批合同仍是
   主因；下一方向标为候选假设，不能写成当前能力或已排期功能。
7. **WHEN** 检查页面源码与 SSR，**THEN** 不出现 `fetch`、表单、输入框、Provider 凭据或创建 run
   入口；现有公开只读回放字段和链接保持不变。
8. **WHEN** 在桌面和窄屏渲染，**THEN** 弧线、证据链接、三维卡片与短板面板保持可读，键盘焦点和
   语义标题 / aria 标签完整；OG 卡片与 v2 主叙事一致。
9. **WHEN** 完成本地实现，**THEN** Web 生产构建 / SSR、Python 全量、编译、园丁、治理、Compose
   config、凭据 / 反向导入和 diff 门全绿，产品与评测资产无差异。
10. **WHEN** 远端流程完成，**THEN** 精确 head 建 Draft PR，api / web / container 全绿后 squash
    合并并复核 main；不得触发任何部署或修改公网运行时。

## Rollback

Revert 本切片提交即可删除新增展示板块、样式、SSR 合同和 OG 卡片；不涉及数据库、API、评测资产或
线上部署回滚。

## Rules restated

- 数字按证据原样展示：开发集满分不等于泛化，`27/30` 必须标为投影，换库成功题必须明示 `0/7`。
- 本片只做静态展示；不运行评测、不调用 Provider、不新增交互能力、不部署。
- 每个数字必须同时回指公开报告回执与 PR；Git 忽略的原始报告只用 run ID / SHA-256 间接证明。

## Frozen evidence map

- `14/20`：[`model-eval-runner.md`](model-eval-runner.md)，PR #9。
- `17/20`：[`training-pair-frozen-eval.md`](training-pair-frozen-eval.md)，PR #19。
- `20/20`：[`intent-routing-fix.md`](intent-routing-fix.md)，PR #20。
- `30/30`：[`unseen-success-fix.md`](unseen-success-fix.md)，PR #23；它是已见错误修复后的开发集。
- `40/40`：[`hardcase-fix.md`](hardcase-fix.md)，PR #25；它是已见 40 题修复结果。
- 换 schema `8/15` / 成功题 `0/7`：[`schema-summary-injection.md`](schema-summary-injection.md)，
  PR #30；结构摘要轮次总分未升且执行率下降。
- 改述投影 `27/30`：[`paraphrase-synonym-coverage.md`](paraphrase-synonym-coverage.md)，PR #29；只复跑
  `ambiguity-001-p1..p3`，由所选 `0/3 → 3/3` 投影旧完整基线 `24/30 → 27/30`。

## Local evidence

- SSR 合同先因 `14/20` 不存在而红；实现后 Web 生产构建 / SSR `3/3` 与 ESLint 零警告通过。
- 页面固定五步与七组报告 / PR 链接；机器合同同时锁定同一 20 题、已见开发集、换库 `0/7`、
  改述投影 / 三题复跑和“候选假设 · 未实现”边界。
- Python `3.13.12` 全量 `120/120`、编译、44 条锁依赖、7 份 strict JSON / JSONL、园丁 current、
  治理、Compose config、凭据 / 反向导入和 diff 门全绿；`api/src`、`evals`、依赖与部署 diff 为零。
- v2 OG 为 `1536×1024`，SHA-256 `DBCD5FB3…BB8AE7`；逐字核验标题、五步分数与开发集边界。
- 公网只读核验仍是 v1 标题且不含验证弧线；本片 Provider 调用、评测运行、服务器写入和部署均为 `0`。

## Remote evidence

待远端流程完成后填写。
