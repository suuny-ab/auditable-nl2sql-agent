# NL2SQL 展示页

当前网页可在本地运行。v2 先用版本化报告与 PR 展示五步调优弧线、三维泛化对照和换库短板，
再用既有 `container-demo-run` 回放“问题 → SQL → 只读执行 → 校验 → 证据 → 回答”完整链路。
页面不创建 run、不调用 Provider，也不连接真实数据。

## 本地启动

需要 Node.js 22.13 或更新版本：

```powershell
npm install
npm run dev
```

开发服务器会输出本地地址。生产构建与 SSR 合同：

```powershell
npm test
```

## 回放来源

- 页面快照：`app/data/container-demo-run.json`
- 公开只读记录：<https://47.84.34.86/nl2sql/api/v1/runs/container-demo-run>
- 公开 health：<https://47.84.34.86/nl2sql/api/v1/health>
- 反向合同：`api/tests/test_web_showcase.py` 使用现有产品 fixture 重新生成同一 run，并核对页面字段。

## 验证弧线口径

- `14/20 → 17/20 → 20/20` 复用同一 20 题开发集；`30/30 → 40/40` 也是观察错误后修复的
  主库开发集成绩，不能当作五轮未见泛化。
- 泛化三维分别是主库已见开发集 `40/40`、换 schema 最新 `9/15`（成功题 `1/7`）和同义改述
  投影 `27/30`（只复跑三条）。换库序列保留结构摘要历史轮 `8/15、0/7`，再分别链接原生注释
  `8/15 → 9/15、0/7 → 1/7` 的[报告](../docs/work/native-metadata.md) / [PR #34](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/34)，以及有限字段值采集保持 `9/15、1/7`
  的[报告](../docs/work/low-cardinality-value-collection.md) / [PR #35](https://github.com/suuny-ab/auditable-nl2sql-agent/pull/35)。
- 原生注释带来一次局部改善；有限字段值只证明没有退化。剩余成功题 `6/7` 的已知缺口集中在金额
  单位、输出列 / 行合同与有界查询 / 审批合同；这些仍是同一换库集合的开发复测，不是新 unseen。

公网当前仍是没有验证弧线的健康 v1；v2 公开事实已在源码候选同步，但本任务不包含部署。
`.openai/hosting.json` 是 Sites 脚手架的空能力声明，`d1/r2` 均为 `null`；v2 页面发布仍需用户
另行当次批准。
