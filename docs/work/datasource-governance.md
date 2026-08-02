# DATASOURCE-GOVERNANCE-039：治理环境按数据源隔离

## Goal

把业务术语、字段备注、枚举索引和训练对迁入显式 datasource 命名空间；生成链只加载绑定到当前
数据源的套装，并使现有主库和第二合成库在迁移前后的离线上下文行为保持一致。

## Non-goals

- 不做数据库元数据爬取、行值扫描、人工标注后台或通用治理流水线。
- 不修改主库 40 题、第二库 15 题、判分器、Provider prompt 策略或安全边界。
- 不调用真实 Provider，不运行冻结评测，不补跑、不刷分；不部署。

## 验收标准

1. **WHEN** 查看包内资源，**THEN** 主库与第二库各自拥有独立目录，目录内均有术语、字段备注、
   枚举索引、训练对和 datasource manifest，根级全局四文件不再存在。
2. **WHEN** 默认生成器处理主库 schema，**THEN** 只加载默认主库 namespace，40 题上下文去掉新增
   namespace 元数据后的规范 JSON SHA-256 仍为
   `29980F9AA5EC0B7AB2E727BC60E7CCAB7FA16EBA107E4D48052C58B57457ABEE`。
3. **WHEN** 绑定第二库 namespace 的生成器处理第二库 schema，**THEN** 只加载第二库自动构建套装，
   15 题上下文去掉新增 namespace 元数据后的规范 JSON SHA-256 仍为
   `1C146DABBA5BE8B20A4B4E9EE2E23FCBFAA12CAE56514CC8ACB0AA0617B65921`。
4. **WHEN** 交叉绑定主库 namespace 与第二库 schema（或反向绑定），**THEN** 在 Provider transport
   调用前失败关闭，且上下文不出现另一库的术语、字段、枚举或训练 SQL。
5. **WHEN** 加载第二库套装，**THEN** 字段备注与候选术语逐项等于当前 deterministic
   `build_schema_knowledge` 产物，枚举和训练对为空，不读取业务行。
6. **WHEN** datasource ID 非法、未知或资源合同漂移，**THEN** 加载失败关闭，不回退到全局知识。
7. **WHEN** 运行 Python 全量、Web、编译、依赖、文档园丁、治理、Compose 与差异检查，**THEN**
   全部通过且 Provider 调用数为 `0`。

## 回滚

revert 本切片 squash commit，恢复根级四份资源和 schema 自动选择逻辑；不迁移或改写运行数据库。

## 规则复述

- 本切片只交付 datasource 治理隔离；新流水线、枚举自动采集和真实评测另立任务。
- Provider 默认禁用；本片真实 Provider 调用、usage、token 和费用必须为 `0`。
- 推送与 Draft PR 只使用本派发夜班授权；候选 CI 全绿后按常设档 squash 合并，不部署。

## 基线证据

- `origin/main@bbe07495bc5bcf5c2a7949b027df84053fb6c66d`；隔离分支
  `agent/datasource-governance`，原工作区只保留用户既有 `AGENTS.md` 修改。
- Python `3.13.12` 知识 / 自动构建定向基线 `25/25` 通过。
- 迁移前主 40 / 第二库 15 上下文规范 JSON 分别为 `46,383 / 25,970` 字节，SHA-256 见 AC 2/3。

## 完成证据

- 新隔离测试先因 `DEFAULT_DATASOURCE_ID` 不存在而红；实现后 datasource 定向 `5/5`、知识 / 自动
  构建 / Provider fake transport 定向 `45/45` 通过。
- 主库根级四文件已迁入 `synthetic-ecommerce-v1/`；第二库的 13 条术语 / 16 条字段备注与当前
  deterministic builder 逐项相等，归入 `schema-holdout-v1/`，其枚举 / 训练对均为空。
- 主 40 / 第二库 15 的迁移等价指纹分别保持
  `29980F9A…7ABEE / 1C146DAB…65921`；交叉绑定两方向均在 fake transport 调用前失败关闭。
- 全量首轮 `124/125`，唯一旧测试仍让默认主库生成器处理第二库；只为该夹具显式绑定第二 namespace
  后，Python `3.13.12` 全量 `125/125` 通过，没有放宽产品隔离。
- Web lint、生产构建 / SSR `3/3`、`compileall`、44 包依赖、71 份 strict JSON、园丁
  `stale=0 / review=0`、治理、Compose config、凭据 / 反向导入与 diff 检查全绿。
- 完整容器验收为非 root `10001:10001`、health `ok`、固定 run 完成、POST `405`、两库哈希不变；
  Windows CRLF 入口仅在构建时临时转 LF，结束后恢复 SHA-256 `1C75B8D2…A3A`，未形成代码差异。
- 容器镜像内两套资源实读为主库 `10 terms / 16 pairs`、第二库 `13 terms / 0 pairs`。真实 Provider
  调用、usage、token、费用、冻结评测和部署均为 `0`。
