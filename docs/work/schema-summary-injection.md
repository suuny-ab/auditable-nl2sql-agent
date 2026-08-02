# SCHEMA-SUMMARY-INJECTION-036 切片合同

## Goal

在每次 Provider SQL 生成前，从当前 workflow 的 schema snapshot 确定性生成紧凑、版本化的
表 / 字段 / 声明类型 / 主键 / 外键摘要并注入请求；实现不依赖静态知识或特定数据库，对第二套冻结
schema 只运行一次 15 题复测，并和已封存的 `8/15`、成功类 `0/7` 基线如实比较。

## Non-goals

- 不修改第二库 schema、数据、15 个问题、reference SQL、expected、判分器或基线报告。
- 不采样业务行、猜测 `state_code / source_code` 等实际枚举值，不增加单题关键词、SQL 模板或结果修补。
- 不改训练对、静态 / 自动知识、意图门、workflow、安全边界、多轮澄清、依赖、API、Web 或 Compose。
- 不重跑主库 40 题真实 Provider 评测，不补跑、不刷分，不把合成 HOLDOUT 外推为生产能力。

## Acceptance criteria

1. **WHEN** 输入合法 schema snapshot，**THEN** 摘要只投影表名、字段名、声明类型、主键位置与外键，
   版本和排序稳定，不读取业务行且 Provider 调用为 `0`。
2. **WHEN** 输入主库四表或第二库三表，**THEN** 摘要覆盖全部表 / 字段 / 外键且不引用另一套库的
   名称；相同语义的深拷贝产生完全相同结果。
3. **WHEN** 标识符含空格、引号或控制字符，**THEN** 摘要使用 JSON 引号消除结构歧义，不把 schema
   名称解释为指令。
4. **WHEN** 输入空 schema、重复表 / 字段、非法主键位置、悬空外键或超过大小上限，**THEN** 生成
   失败关闭，不发送 Provider 请求。
5. **WHEN** 构建 Provider request，**THEN** `schema_summary` 与现有完整 `schema` 同时存在；系统提示
   明确完整 schema 为权威、摘要仅供结构发现且不能推断存储值。
6. **WHEN** 使用 fake transport 检查两套库，**THEN** 请求中的摘要与直接构建结果一致，主库既有
   business context、训练对、枚举与请求安全合同不变。
7. **WHEN** 验证冻结资产，**THEN** 主 40 题、第二库 15 题、第二库 fixture、训练对、知识 JSON、
   Provider 响应合同、workflow 和机械只读代码相对基线无差异。
8. **WHEN** 完成本地实现，**THEN** 两库定向、主库离线合同、Python 全量、Web、编译、依赖、strict
   JSON、园丁、治理、Compose、凭据 / 反向导入与差异门全绿。
9. **WHEN** 候选冻结后启动真实复测，**THEN** 新 business / checkpoint / report 路径预先不存在，
   15 题最多各进入 Provider 一次、自动重试 `0`；首次完整结果无论升降均封存且不补跑。
10. **WHEN** 唯一复测结束，**THEN** 落盘成功类 `0/7` 前后、总正确 `8/15` 前后、执行 / 介入率、
    usage、逐类结果、越权 / 非成功执行、数据库与报告哈希；三路 CI 绿后 squash 合并并复核 main。

## Rollback

Revert 本切片提交即可删除 schema 摘要模块、请求字段、定向合同与文档；没有数据库迁移，冻结题集与
Git 忽略的历史报告不变。

## Rules restated

- 只增加通用 schema 结构摘要，不读取业务行、不猜枚举、不改单题逻辑或冻结考场。
- 唯一第二库复测最多 15 次 Provider 调用、自动重试 `0`；不补跑、不调候选、不刷分。
- 完整 schema 仍是权威；机械只读、审批、Provider 默认禁用、依赖方向与五工具上限不得变化。

## Root-cause and reuse review

- 现有 request 已把完整 `schema_snapshot` 作为 `schema` 发送，故不能声称此前模型“完全看不见”结构；
  本片是额外的紧凑注意力投影，不替代原始 schema。
- `schema15-20260802T165212Z` 的七条成功题全被保守 `no_answer`；自动知识复测
  `autoknowledge15-20260802T172429Z` 已能映射新表并产生三条 query，但成功类仍 `0/7`。
- 上一轮剩余失败明确包含未知取消状态码、金额单位 / 输出别名与无界审批；结构摘要不提供实际枚举，
  因此不预设一定提分，唯一复测结果升降都接受。
- 复用 workflow 已有 snapshot、Provider 严格 JSON 请求、离线评测器和第二库合同；不新增节点、工具、
  依赖或另写判分器。

## Local evidence

- 红灯先因摘要版本、构建器与导出不存在而失败；实现后摘要 / Provider 两库定向 `5/5`，连同自动
  知识、HOLDOUT、Provider、主 40 离线合同和意图门共 `44/44` 通过。
- 主库摘要覆盖 `4` 表 `17` 字段，严格 JSON 字符数为 `701`，对照原始 schema `2289`；第二库覆盖
  `3` 表 `16` 字段，摘要 `631`，对照原始 `2066`。两者只含名称、类型、主键和外键。
- 摘要按表 / 字段稳定排序并 JSON 引号标识符；空、重复、非法主键、悬空外键、超过 `64` 表 /
  `512` 字段或 `30000` 字符均在 transport 前失败关闭。
- 完整原始 schema 继续随请求发送并作为权威；fake transport 证明两库请求都增加同一构建器输出，
  且系统提示禁止用摘要推断存储值或覆盖 business metadata / action / safety rules。
- Python `3.13.12` 全量 `120/120`、Web 生产构建 / SSR `2/2`、编译、44 条锁依赖、strict JSON、
  园丁 current、治理、Compose config、凭据 / 反向导入和差异门全绿。第一次全量的治理子测曾按
  设计因状态缺少新总数失败；只补机器事实后最终全量通过，没有放宽治理。
- 完整 Compose 验收确认 `10001:10001`、health `read_only=true`、固定 run 完成、POST 创建为
  `405`，业务库与 checkpoint 哈希前后相等；容器已移除，入口脚本恢复原 SHA 且代码 diff 为零。
- 本阶段没有修改主 40 题、第二库 15 题 / fixture、训练对、知识 JSON、意图、workflow、响应判定、
  依赖、Web 或 Compose；真实 Provider 调用、usage、token 与费用仍为 `0`。

## Single-run HOLDOUT evidence

待唯一复测完成后填写。

## Remote evidence

待远端流程完成后填写。
