# 当前开发状态

> 只保存当前事实；历史证据与回执见 [`docs/status-log/`](status-log/)，稳定边界见 [`PROJECT.md`](../PROJECT.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `in-review` |
| 更新时间 | `2026-08-03` |
| 当前切片 | `SCHEMA-KNOWLEDGE-BUILDER-033`：规则式 schema 知识自动构建与一次换库复测 |
| 最近完成 | `SCHEMA-HOLDOUT-032`：PR #26 合并为 `f6d30aa2`，main 三个 CI job 全绿 |
| 当前状态 | 自动构建器与两库接入已完成本地验证；真实复测尚未启动，Provider 调用为 `0` |
| 完成门 | 唯一 15 题复测如实落盘；推送精确结果 head、Draft PR 三路 CI 全绿后 squash，并复核 main CI |
| 项目基线 | `origin/main@f6d30aa2d01d624db08759fc3a61564b8e7a59cc`；main CI run `30757756183` 成功 |
| 阻碍 | 无；本单授权最多 15 次 Provider 调用、自动重试 `0`，不补跑、不改单题或第二库考场 |

## 当前队列

- `schema-derived-knowledge-v1` 只读 schema metadata，从命名、类型、主键和外键稳定生成全部字段
  备注初稿与候选术语；不读取业务行、不调用 LLM、不猜闭集枚举实际存储值。
- 主库完整 / 子集 schema 继续使用原静态知识、枚举和 16 条训练对；陌生 schema 才使用自动知识，
  旧表训练 SQL 不进入第二库 Provider 请求。
- 第二库 16 个字段全部生成备注，候选术语覆盖订单、客户、商品、日期、状态、渠道、数量、实际成交价、
  目录标价、区域、分群、销售额和客单价；所有引用均存在于输入 schema。
- 定向自动知识 / 主库知识 / Provider 请求共 `39` 项通过；Python 全量 106 项测试通过，Web `2/2`、
  编译、44 包依赖、strict JSONL、园丁、治理和完整只读 Compose 验收全绿。
- 现有 40 题、第二库、15 题 HOLDOUT、16 条训练对、意图门、Provider adapter、工作流、依赖和
  Compose 合同相对 `origin/main` 零差异；本阶段真实 Provider 调用、usage、token 与费用为 `0`。
- 复测输入继续使用上一轮已验证的 LF 冻结副本 SHA-256 `3a598167…7bb16`；第二库哈希固定
  `ed9a2cda…78143d`，对比基线为执行 `0/7`、正确 `6/15`、介入 `2/15`。

## 下一检查点

- 冻结本地候选，确认全新 checkpoint / report 不存在后，仅运行一次第二库 15 题复测。
- 结果升降如实写入两层状态；不补跑、不改单题，然后按授权推送、建 Draft PR、CI 绿后 squash。
