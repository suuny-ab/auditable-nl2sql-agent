# 文档园丁首次扫描报告

> 日期：`2026-08-02`
>
> 基线：`origin/main@4e9ec9ded60793dad12521aa7d7c9467ad44d042`
>
> 性质：只读治理扫描；不是产品、模型、部署或生产健康证明。

## 扫描合同

合并门命令：

```powershell
python tools/doc_gardener.py --scope current --format markdown --fail-on stale
```

手动全扫命令：

```powershell
python tools/doc_gardener.py --scope all --format markdown
```

canonical 输入只有 `PROJECT.md` 与 `docs/status.md` 当前层。合并门扫描 `AGENTS.md`、根 README、
deploy / evals / web README、`docs/engineering/` 和 `docs/work/README.md`；手动全扫再加入历史工作
合同，但排除 append-only 状态日志与扫描报告自身，避免报告引用 findings 后递归放大。工具只报告，
不自动修改任何文档。

## 首次结果

- 活动文档：扫描 `9` 个文件，`stale=0`、`review=0`，因此没有可由 canonical 明确裁决的腐坏，
  本轮没有直接改写活动文档。
- 手动全扫：扫描 `29` 个文件，`stale=0`、`review=7`。以下 7 项都位于已完成的历史
  切片合同；它们可能只是当时语境，也可能会被误读为现行事实，机器不能无损裁决，因此原文未改。
- canonical 全量测试数在开工时为 `60`；新增 5 项园丁回归通过后，最终当前层登记为 `65`。
- 实现初扫曾把“同时出现在”误识别为“现在”，并把“当前状态 / 当前切片 / 当前工作树”等规则
  元语句列为 review；已修扫描逻辑而非改写原文，回归测试固定这些非误报边界。

## 已修清单

- 活动文档确定腐坏：无。
- 扫描器误报：把 `现在` 限定为不属于“出现在”的独立相对时间词；规则元语句和带日期 / 本轮 / PR
  等同一行时间锚的历史描述不再进入 `stale` 或 `review`。

## 待裁决清单

| 位置 | 2026-08-02 首扫引用 | 为什么不擅改 |
| --- | --- | --- |
| `docs/work/deepseek-provider-probe.md:45` | 2026-08-02 原文：“当前 Chat Completions 文档列出的模型……” | 可能是探针时点事实，也可能被理解为现行型号；需决定是否补探针日期 |
| `docs/work/deepseek-provider-probe.md:47` | 2026-08-02 原文：“当前 OpenAI-compatible base URL……” | URL 属外部易变事实；本片不联网重写历史合同 |
| `docs/work/deepseek-provider-probe.md:52` | 2026-08-02 原文：“这是当前凭据、网络、接口……可行性探针” | “当前”可能限定探针运行时点；替换会改变原证据语义 |
| `docs/work/deepseek-sql-generator.md:20` | 2026-08-02 原文：“当前已授权的环境变量” | 授权只对当时轮次有效；需决定是否改为“该轮已授权” |
| `docs/work/docker-compose-readonly-api.md:61` | 2026-08-02 原文：“本项目当前演示数据库……” | 可能描述切片时实现，也可能意指现行镜像合同；需由维护者选择时态 |
| `docs/work/evidence-fingerprint-probe.md:39` | 2026-08-02 原文：“使用当前产品代码创建……” | 可能是探针时点快照；需决定是否绑定对应提交 |
| `docs/work/status-two-layers.md:25` | 2026-08-02 原文：“当前 55 项基线全部通过” | 数字属于该切片验收时点，但“当前”可能被误读为现行全量数；需决定是否改为“切片基线” |

## 能证明与不能证明

本报告证明：已登记的 main SHA、项目 / 工作流状态、活动切片、全量测试数、网页可用性、合成数据
边界和 Provider 默认值发生明确相反的相对时间主张时，测试与治理门会失败；手动全扫能稳定列出
历史合同中的相对时态。

它不证明 canonical 输入自身一定及时，也不理解任意自然语言语义；7 个 review 不阻断合并，任何
措辞修改仍需人工对照当时证据。Provider 调用、token、费用、真实数据与部署均为 `0`。
