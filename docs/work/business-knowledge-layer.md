# BUSINESS-KNOWLEDGE-LAYER-019 切片合同

## Goal

用两份版本化合成知识文件表达约 10 条电商术语和 4 张表全部字段的业务备注，并把问题命中的
术语定义及其相关字段备注有界注入现有 DeepSeek SQL 生成请求；在不改变工作流和安全边界的
前提下复跑冻结 20 条评测，正确率不得低于首次 `14/20`。

## Non-goals

- 不做枚举值索引、训练对、偏好、记忆、技能或网页。
- 不改 LangGraph 节点、审批门、只读执行器、evidence/answer 合同或评测集文本与判定口径。
- 不调参、不为结果补跑、不增加 Provider 自动重试，也不宣称同一冻结集上的泛化提升。
- 不接真实数据，不新增费用渠道或代码层预算配置。

## Acceptance criteria

1. **WHEN** 校验业务术语文件，**THEN** 恰有 10 条唯一术语，每条都有同义词、非空定义和已知
   `table.column` 引用。
2. **WHEN** 校验字段备注文件，**THEN** `customers/products/orders/order_items` 的 17 个现有字段
   各有且仅有一条非空业务备注，没有未知表或字段。
3. **WHEN** 问题命中术语或同义词，**THEN** Provider 输入只包含命中术语的定义及其去重、稳定排序
   的相关字段备注，不注入未命中术语。
4. **WHEN** 问题未命中任何术语，**THEN** 业务上下文为空列表，schema 与原安全 prompt 仍照常
   提供，不能因知识缺失绕过失败关闭。
5. **WHEN** 使用 fake transport 运行定向测试，**THEN** 能从发送的严格 JSON 中证明术语命中、
   同义词命中、字段备注注入和无关知识排除。
6. **WHEN** 运行 Python 3.13 全量测试，**THEN** 全部通过；`compileall`、`pip check`、数据 JSON
   严格解析、wheel 包含两份知识文件与 `git diff --check` 均通过。
7. **WHEN** 获得一次性 Provider 授权并复跑冻结评测，**THEN** 恰好 20 个 case、自动重试 `0`，
   业务库逐案例与整轮哈希不变，正确率至少 `14/20`，usage 与误差如实落盘。
8. **WHEN** 远端分支精确 head 的 Python/container CI 全绿，**THEN** 按常设档 squash 合并；否则
   不合并。

## Rollback

Revert 本切片提交即可移除两份知识文件、loader 和 Provider 输入字段；工作流、审批门、数据库与
冻结评测集没有迁移。真实评测报告留在 Git 忽略目录，不进入仓库。

## Rules restated

- 只用合成知识和合成数据库；机械只读与审批边界不得被提示知识覆盖。
- 新 Provider 调用按授权请求档处理；未获批准前实现和离线测试可继续，真实调用为红线。
- 本单只授权当前有界分支的 push、Draft PR 与精确 head CI 绿后的 squash 合并；不部署。

## Reuse review

- 复用现有 `DeepSeekSqlGenerator` 的严格 JSON 请求、默认禁用、fake transport、脱敏 usage 和零重试
  合同；不新增工具或工作流节点。
- 复用现有 schema snapshot 中的稳定 `table/column` 名称作为字段引用权威；知识文件只补业务含义，
  不复制类型、主外键或运行数据。
- Traceable 没有可直接复用的本项目电商术语资产；本片使用标准库 `json` 与
  `importlib.resources` 的薄 loader，避免新增依赖。

## Local evidence

- 两份 strict JSON 分别钉定 `business-terms-v1` 与 `field-descriptions-v1`；loader 验证精确字段、
  非空文本、术语/同义词唯一性、字段唯一性及所有术语引用存在。
- 数据合同定向测试证明恰有 10 条术语，4 张 demo 表的 17 个字段备注完整且无额外字段；同义词
  `营收/有效订单/渠道` 命中后只注入相关 7 个字段，未命中问题得到两个空列表。
- fake transport 从真实 Provider request 解码 `business-context-v1`，证明 `GMV` 命中、相关字段
  稳定排序、无关“客户分群”未进入请求；Provider 仍默认禁用且不读取凭据。
- Python `3.13.12` 全量 `59` 项测试通过；`compileall`、`uv pip check`、两份 strict JSON 解析和
  `git diff --check` 通过。构建 wheel 后确认两份知识文件均在包内。
- Windows 检出的入口脚本含 CRLF，首次两次本地 Compose 启动均以 `127` 退出；字节与直接容器
  报错确认是已知 shebang 问题后，仅把当前工作树脚本规范化为与 Git blob 相同的 LF（最终代码
  diff 为零）。第三次也是最后一次尝试达到 Healthy，health 返回 `read_only=true`，固定 run 为
  `container-demo-run/completed/run-record-v5`，随后只清理本切片 Compose 项目。
- 一次性真实 20 条评测尚未获授权，因此 Provider 调用、token 和费用均为 `0`；授权请求已写入
  `派发/授权请求.md`，未把这一步的缺失写成效果已验证。
