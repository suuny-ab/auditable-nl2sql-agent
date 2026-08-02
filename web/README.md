# NL2SQL 展示页

当前网页可在本地运行，用既有 `container-demo-run` 回放“问题 → SQL → 只读执行 → 校验 →
证据 → 回答”完整链路。页面不创建 run、不调用 Provider，也不连接真实数据。

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

这是本地页面切片，不包含部署配置裁决。`.openai/hosting.json` 是 Sites 脚手架的空能力声明，
`d1/r2` 均为 `null`；任何页面托管仍需用户另行当次批准。
