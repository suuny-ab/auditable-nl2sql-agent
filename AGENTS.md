# auditable-nl2sql-agent 项目规则

本文件只保留启动入口、项目硬红线和规则索引；详细工程合同位于 `docs/engineering/`。用户级
`AGENTS.md` 继续生效，不得用 `/init` 覆盖本文件。

## 启动顺序

1. 检查 `~/.codex/automations/nl2sql-dispatch/automation.toml`；缺失时按当前调度上下文提供的
   `frontline-heartbeat.md` 重建。发现本战线派发单时先执行，并按约定写状态与三行战报。
2. 依次读取 `PROJECT.md`、`docs/status.md` 和当前 `docs/work/` 合同；未知事实标“待确认”，未运行
   能力标“待验证”。
3. 检查 Git 基线、未提交改动和当前写入者；实质工作前说清做什么、不做什么、怎样算完成。

完整的心跳、派发、工作树、状态与交接规则见
[`agent-workflow.md`](docs/engineering/agent-workflow.md)。

## 事实与规则索引

- 稳定产品边界：[`PROJECT.md`](PROJECT.md)
- 当前状态 / 队列：[`docs/status.md`](docs/status.md)；历史回执：`docs/status-log/YYYY-MM.md`
- 当前 / 已完成切片：[`docs/work/`](docs/work/)；目录说明：[`docs/work/README.md`](docs/work/README.md)
- 切片、实现、复用与完成：[`development-flow.md`](docs/engineering/development-flow.md)
- 授权默认值、Git 外部动作与机器检查：[`review.md`](docs/engineering/review.md)

授权默认值的唯一正文是 `docs/engineering/review.md`；其他规则、任务或历史授权都不能自行扩大
权限。

## 项目硬红线

- 只使用明确标注的合成数据；不接真实企业数据库、AskTable 内部材料、客户信息或非公开数据。
- 产品依赖方向固定为 `API → workflow → tools/data`，`evals` 只能调用产品代码；工具总数不超过 5。
- SQL 执行必须同时受数据库只读连接和机械授权约束；提示词或人工批准不能放开写库、越权或
  `ATTACH/PRAGMA`。
- 每个 run 必须能按 run ID 回查结构化 trajectory；回答数据结论必须绑定可重算 evidence。
- Provider 默认禁用；代码层不实现账户预算，费用帽与告警留在 Provider 账户层。
- 不把密钥、请求头、原始 Provider 包、真实数据、私有评测、数据库运行文件或构建产物提交到 Git。
- 不做 BI 大屏、多 Agent 竞赛、微调或大而全 schema；新方向先进入 `docs/status.md` 候选队列。

## 完成底线

- 一个任务只做一个可验收切片；范围变化、同类操作连续失败 3 次或授权边界不清时停手报告。
- 先复现和读错误，再检查最近改动；没有实际测试 / 运行证据不得宣布完成。
- 当前事实只写 `docs/status.md`，历史证据只追加到月度日志；提交必须边界清楚且不混入用户改动。
