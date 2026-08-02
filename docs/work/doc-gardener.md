# DOC-GARDENER-021 切片合同

## Goal

按 NL2SQL 的 `PROJECT.md` 与 `docs/status.md` 当前层裁剪 Traceable PR #58 的只读文档园丁，
让确定的当前态矛盾阻断合并，同时提供不会自动改文档的手动全扫与首次报告。

## Non-goals

- 不改产品代码、评测、业务知识层、Provider、依赖或容器合同。
- 不新增定时任务、外部服务、自然语言模型判断或大规模文档改写。
- 不把启发式扫描写成事实源；工具只消费项目已有事实源，不替代人工维护它们。

## Acceptance criteria

1. **WHEN** 运行默认园丁扫描，**THEN** 只读加载 `PROJECT.md` 与 `docs/status.md`，确定性扫描活动
   文档并输出稳定 Markdown 或 JSON 报告。
2. **WHEN** 活动文档用“当前 / 目前 / 现在 / 现行”声称与登记基线、切片、测试数、网页、数据或
   Provider 默认值冲突，**THEN** 产生 `stale` finding，门禁以非零退出。
3. **WHEN** 运行手动 `--scope all`，**THEN** 扫描全部非状态日志 Markdown，把历史合同中缺少
   时间锚的相对当前态措辞列为 `review`，但不自动修改。
4. **WHEN** 首扫发现确定腐坏，**THEN** 只按 canonical 来源修正；语义拿不准的项逐条进入首次
   报告待裁决清单。
5. **WHEN** 运行治理检查，**THEN** 现有规则索引断言与园丁 `stale` 门同时通过；新增回归测试
   证明冲突失败、匹配与历史锚不误报、报告确定。
6. **WHEN** 运行全量测试，**THEN** 既有 60 项与新增园丁测试全部通过，`compileall`、依赖、
   diff 和范围检查通过。
7. **WHEN** 精确远端 head 的 `api` 与 `container` CI 全绿，**THEN** 按本单授权 squash 合并；
   否则不合并。

## Rollback

Revert 本切片提交，删除园丁脚本、测试和首扫报告，并恢复治理检查 / 工程说明即可；产品与数据
没有迁移。

## Rules restated

- 确定矛盾才阻断并按事实源修正；拿不准只列 `review`，工具永不改写文档。
- 只复用 Traceable PR #58 的扫描 / 分级 / 确定性报告结构，不复制其发布、HOLDOUT 或生产字段。
- 本单只授权当前分支一次 push、一个 Draft PR 和精确 head 双 CI 绿后的 squash；不部署、不调
  Provider、不自动开工网页。

## Reuse review

- Traceable PR #58 已以 merge SHA `31541cfa` 合入；复用其纯标准库 dataclass、Markdown / JSON
  renderer、`stale` / `review` 分级和只读 CLI 结构。
- NL2SQL 没有 `release_sha` / `live_experience` / product release 合同，因此改为项目状态、
  当前切片、main 基线、全量测试数、网页、合成数据与 Provider 默认值；CI 也按本单要求对 `stale`
  失败，而不是照搬 Traceable 的 advisory hook。

## Local evidence

- `current` 扫描 9 个活动文档，`stale=0/review=0`；`all` 扫描 29 个非状态日志 Markdown，
  `stale=0/review=7`。确定腐坏为 0，7 个无法机器裁决的历史相对时态保持原文并逐条进入
  `doc-gardener-initial-report-20260802.md`。
- 5 项新增测试证明 main SHA、state、活动切片、全量测试数、网页、真实数据和 Provider 默认启用
  等 7 类反向主张形成 `stale`；匹配主张、历史锚和“同时出现在”不误报；CLI 门在 stale 时返回 1。
- 治理检查返回 `doc_gardener_stale=0`，CI 的 `api` job 新增同一显式失败门。Python `3.13.12`
  全量 `65` 项通过；`compileall`、44 包依赖检查、Compose config 和 `git diff --check` 通过。
- 首次全量误用系统 Python 3.14，错误为缺少锁定 checkpoint 模块；定位解释器后使用既有 3.13.12
  锁环境通过，没有改依赖或连续猜修。
- `api/src/auditable_nl2sql`、`evals`、知识文件、依赖、Compose、deploy 与 web 差异均为 `0`；
  Provider 调用、token、费用、真实数据、部署和定时任务也均为 `0`。
