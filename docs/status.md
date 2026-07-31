# 当前开发状态

> 本文件只保存当前事实、验证证据和下一检查点。稳定边界见 `PROJECT.md`。

| 字段 | 内容 |
| --- | --- |
| `state` | `ready` |
| 更新时间 | `2026-07-31` |
| 最近完成 | `READONLY-SQL-001`：合成 SQLite 数据、schema 读取、只读 SQL 执行 |
| 做什么 | 建立可重复数据库事实层，并用数据库只读模式和 SQLite authorizer 双层拦截写操作 |
| 不做什么 | 本切片不接 LangGraph、LLM、FastAPI、trajectory、审批页面、Docker 或真实数据 |
| 完成门 | 4 表 schema 可读；固定聚合查询结果可复验；写/DDL/ATTACH/PRAGMA 被拒且数据未变化；行数硬上限有测试 |
| 风险 | `R0`：仅本地合成数据，无网络、费用、Provider 或外部写入 |
| 项目基线 | 公开仓库 `suuny-ab/auditable-nl2sql-agent`；`origin/main` 为 `429b440` |
| 阻碍 | 无 |

## 复用审查

- 已复用 Traceable 的 `api/src + api/tests` 布局、稳定事实/当前状态分离、失败关闭测试思路和
  只读 GitHub Actions 权限姿态。
- Traceable 没有可直接复用的 NL2SQL 只读执行器；本切片使用 Python `sqlite3` 的 URI
  `mode=ro`、`PRAGMA query_only` 和 authorizer 组成薄适配层。
- 暂不搬运其完整发布证明、Provider 预算、部署和多工作区治理；这些不属于当前完成门。

## 验证证据

- `PYTHONPATH=api/src python -m unittest discover -s api/tests -p "test_*.py" -v`：
  `Ran 8 tests in 0.259s`，`OK`。
- `python -m compileall -q api/src`：退出码 `0`。
- CLI 冒烟：创建 `.local/cli-demo.sqlite3` 后读回
  `tables=customers,order_items,orders,products`、`orders=6`。
- 测试内固定表行数为 `4 / 5 / 6 / 11`、聚合结果为 `5946.0`；7 类越界语句被拒绝，
  随后订单数和 4 表 schema 均未变化。
- `.github/workflows/ci.yml` 已配置 Python 3.13 编译和相同单测；远端当前结论以
  [GitHub Actions](https://github.com/suuny-ab/auditable-nl2sql-agent/actions/workflows/ci.yml)
  为准，不得把本地绿色写成远端 CI 已通过。
- 首次公开推送 SHA `429b44007e7848317fcccd3199a168ff97fc8075`；GitHub Actions
  [run 30628166219](https://github.com/suuny-ab/auditable-nl2sql-agent/actions/runs/30628166219)
  在该 SHA 上完成，结论为 `success`。

## 下一候选

下一切片候选是定义 LangGraph 最小状态、确定性 stub 节点与持久化 trajectory，让一次运行可
按 run ID 回查并验证失败终态。FastAPI、审批门、评测、网页与 Docker 按依赖顺序后续进入，
不在本轮顺手实现。
