# NATIVE-METADATA-040：SQLite 原生注释爬取与分层合并

## Goal

让只读 schema 爬取器同时读取 SQLite 表 / 字段的 DDL 原生注释，并在第二 datasource 的自动知识
构建中按“原生注释优先、生成备注回退、无可用内容则空”合并；冻结候选后只执行一次第二库 15 题
复测，与最新 `8/15` 如实对比。

## Non-goals

- 不实现人工标注、覆盖 UI、元数据定时任务或跨数据库方言适配。
- 不从业务行猜枚举 / 描述，不针对单题改规则，不改 40 / 15 题、gold、判分器或 Provider action。
- 不补跑、不刷分、不部署；本轮 Provider 最多 15 次，自动重试固定为 `0`。

## SQLite 能力边界

- SQLite 官方说明 `sqlite_schema.sql` 保存创建对象的原始 `CREATE` 文本（仅做列明的规范化）；官方
  也定义 `--` 与 `/* ... */` 注释为可出现在空白处的 SQL 语法。
- SQLite 的 `CREATE TABLE` / `PRAGMA table_xinfo` 没有独立 description/comment 字段。因此本片将
  `sqlite_schema.sql` 中与表名或字段定义直接相邻的 DDL 注释定义为“SQLite 原生注释”；这是基于
  官方存储与语法合同的保守适配，不声称 SQLite 有标准 COMMENT ON 元数据。
- 参考：<https://www.sqlite.org/schematab.html>、<https://sqlite.org/lang_comment.html>、
  <https://www.sqlite.org/pragma.html#pragma_table_xinfo>。

## 验收标准

1. **WHEN** 只读打开含 DDL 注释的任意 SQLite 文件，**THEN** `read_schema` 返回表 / 字段描述且
   读取前后数据库 SHA-256 不变。
2. **WHEN** DDL 使用行注释、块注释、引号标识符、字符串字面量或嵌套约束括号，**THEN** 只提取
   与表名 / 字段定义直接相邻的真实注释，不把字符串或 CHECK 内注释误当描述。
3. **WHEN** DDL 没有注释或注释位置含糊，**THEN** 描述为 `null`，schema 原有名称、类型、主外键
   与默认值合同不变。
4. **WHEN** 自动知识同时有原生注释和生成备注，**THEN** 表 / 字段描述精确采用原生注释并标记
   `native`；无原生注释时采用现有备注并标记 `generated`。
5. **WHEN** 输入描述为空、字段悬空或 native metadata 类型错误，**THEN** 构建失败关闭或安全回退，
   不跨 datasource 加载、不读取业务行。
6. **WHEN** 重建第二库治理产物，**THEN** 原生注释覆盖指定表 / 字段，其余字段仍用 deterministic
   builder；主库 40 题上下文迁移指纹不变，第二库 15 题 / gold 不改。
7. **WHEN** 完成本地实现，**THEN** Python 全量、Web、编译、依赖、strict JSON、园丁、治理、
   Compose、凭据 / 反向导入与容器验收全绿，真实 Provider 调用仍为 `0`。
8. **WHEN** 候选冻结后开始复测，**THEN** 新 business / checkpoint / report 路径预先不存在，
   15 个 case 各最多调用一次，自动重试 `0`，首次完整结果封存且不补跑。
9. **WHEN** 唯一复测结束，**THEN** 记录 `8/15 → 实测值`、成功类、执行 / 介入率、五类正确数、
   prompt / completion / total usage、越权与非成功 SQL 执行、数据库与报告哈希。
10. **WHEN** 结果无论升降，**THEN** 不据结果修改候选；使用夜班授权推送 / Draft PR，三路 CI
    全绿后 squash 合并并复核 main，不部署。

## 回滚

revert 本切片 squash commit，恢复无描述字段的 schema 投影、第二库无注释 DDL 与原生成备注；
运行数据库和 Git 忽略评测回执不做迁移或覆盖。

## 规则复述

- SQL 元数据读取继续使用 `mode=ro + query_only`，不得因注释解析放开写入或读取业务行。
- 唯一第二库复测最多 15 次 Provider 调用、自动重试 `0`；不补跑、不调题、不刷分。
- 人工覆盖位只在合同里保留，当前切片不实现；推送 / PR 使用本单预授权，合并后不部署。

## 基线

- `origin/main@d122a0571bccbf7ca3901122a6bb9778b47b5ef7`；隔离分支
  `agent/native-comment-metadata`，原工作区仍只有用户既有 `AGENTS.md` 修改。
- 最新第二库复测 `schemasummary15-20260802T184047Z`：正确 `8/15`、成功 `0/7`、执行 `2/7`、
  介入 `4/15`，usage `23925 / 1367 / 25292`。
- 当前实现只读表 / 字段结构但没有描述字段；第二库 namespace 的 16 条备注全部是生成产物。

## 本地候选

- `read_schema` 继续经 `mode=ro + query_only` 读取结构，同时从 `sqlite_schema.sql` 保守解析表名 / 字段
  名紧邻的行或块注释；引号标识符、字符串字面量、嵌套约束与无注释回退已有定向合同，读前后数据库
  SHA-256 不变。
- `schema-derived-knowledge-v2` 显式返回 `native / generated / empty` 来源；第二库 3 张表、16 个字段
  全部由 DDL 原生注释重建，主库上下文旧指纹仍为 `29980F9A…7ABEE`，第二库新指纹锁为
  `F62CDCC0…A27C7`，题目、gold、判分器和业务行均未修改。
- Python `3.13.12` 定向 `6/6`、全量 `131/131`；Web lint、build / SSR `3/3`、编译、44 包依赖、
  19 个 JSON / JSONL 文件 strict 解析、园丁 current `9/0/0`、治理、Compose config、凭据 /
  反向导入与 diff 门全绿。
- 完整容器验收为 non-root `10001:10001`、health / list / detail 正常、POST `405`、两库哈希不变。
  首次因 Windows 检出脚本为 CRLF 无法 exec；第二次服务与 HTTP 合同已通过但 PowerShell 数组比较
  误报；修正验证器后的第三次逐项全绿，Compose 现场已清理，入口脚本代码 diff 为零。
- 候选冻结前真实 Provider 调用、usage、token、费用均为 `0`；下一步只消费一次 15 题复测，自动
  重试 `0`，不补跑、不据结果改候选。
