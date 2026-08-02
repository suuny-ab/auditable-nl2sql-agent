# WEB-SHOWCASE-REPLAY-022 切片合同

## Goal

交付一个本地可启动的静态项目展示页，让面试官无需读源码即可看懂“自然语言问题 → SQL → 只读
执行 → 证据 → 回答”的真实回放，并能沿 run ID 回查来源。

## Non-goals

- 不增加交互式问答、run 创建、审批写入、Provider 调用或 API 产品路由。
- 不改评测合同 / 数字、业务知识层、数据库、容器或安全边界。
- 不部署页面，不改 Caddy / 服务器 / DNS；hosting 另行取得用户当次批准。
- 不声称生产级、真实企业数据、泛化提升或未验证准确率。

## Acceptance criteria

1. **WHEN** 在 `web/` 运行 `npm run dev`，**THEN** 一条命令启动单页展示，桌面与移动宽度均可读，
   主要导航与外链有可访问名称。
2. **WHEN** 查看首屏，**THEN** 一句话主张、合成数据 / 只读 / 静态回放边界和证据入口无需读源码
   即可理解。
3. **WHEN** 查看回放，**THEN** 页面展示公开既有 `container-demo-run` 的问题、SQL、结果、证据
   指纹、回答和 8 步 trajectory；`assess_sql` 审批门明确标注本次无需人工介入。
4. **WHEN** 检查静态回放资产，**THEN** Python 合同用现有 fixture 重新生成同一 run，并逐字段核对
   ID、SQL、结果、指纹、答案和 trajectory，证明页面数据不是手写伪造。
5. **WHEN** 点击证据入口，**THEN** 源码仓库、公开只读 health、公开 run 回查和冻结评测证据均指向
   已验证地址；页面不发起创建 run 或 Provider 请求。
6. **WHEN** 运行 `npm test` 与 Python 3.13 全量测试，**THEN** 生产构建、SSR HTML 合同、回放合同
   和既有测试全部通过；园丁 current 门也通过。
7. **WHEN** 检查差异，**THEN** `api/src`、`evals`、知识层、依赖锁、Compose、deploy 与现有容器
   合同均为零改动；页面依赖只存在 `web/`。
8. **WHEN** 精确远端 head 的 `web`、`api` 与 `container` CI 全绿，**THEN** 按本单授权 squash
   合并；否则不合并。

## Rollback

Revert 本切片提交即可删除静态站点、回放快照和对应测试 / 文档；API、数据和部署无需迁移。

## Rules restated

- 回放只取既有合成只读 run，并用产品 fixture 反向验证；不伪造轨迹，不接真实数据。
- 页面只展示与链接，不增加写接口、交互问答、Provider 或部署。
- 本单只授权当前精确候选一次 push、一个 Draft PR 和双 CI 绿后的 squash；新 head 或部署另行授权。

## Implementation choice

- 按 `sites-building` 的现有项目 capability path 在 `web/` 保留独立 Vinext / Vite 结构；用户明确
  local-only，因此不使用 hosting 流程。
- 不需要持久化、鉴权、上传、D1 / R2 或客户端状态；用构建期 JSON 快照和服务器组件保持静态。

## Local evidence

- `npm test`：Vinext 生产构建成功，2 项 SSR / 脚手架合同通过；动态 metadata 指向当前 host 的
  `/og.png`。
- Python `3.13.12` 全量 `69` 项通过；其中 fixture 反向核对公开回放的 run ID、SQL、结果、证据
  指纹、回答与 8 步 trajectory。
- `compileall`、44 包依赖检查、治理检查、Compose config 与 `git diff --check` 通过。
- 园丁 current 扫描 9 个文件为 `stale=0/review=0`；手动全扫 30 个文件为
  `stale=0/review=7`，均为原有历史相对时态，没有擅改。
- 变更没有触及 `api/src`、`evals`、业务知识 JSON、Python 依赖、Compose 或部署配置；没有
  Provider 调用、费用、真实数据或服务器写入。
