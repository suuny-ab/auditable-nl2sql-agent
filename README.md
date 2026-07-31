# auditable-nl2sql-agent

[![CI](https://github.com/suuny-ab/auditable-nl2sql-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/suuny-ab/auditable-nl2sql-agent/actions/workflows/ci.yml)

一个只使用合成数据的可审计 NL2SQL 作品集项目。当前首切片先把最底层事实做实：确定性电商
数据库、schema 读取和机械只读 SQL 执行；完整 Agent 工作流尚未实现。

## 当前目录

```text
api/       Python 产品代码与测试
docs/      当前状态和有界切片合同
evals/     固定合成评测集（待实现）
web/       最小任务/轨迹页面（待实现）
deploy/    Docker 一键启动（待实现）
```

## 本地验证

```powershell
$env:PYTHONPATH = "api/src"
python -m unittest discover -s api/tests -p "test_*.py" -v
python -m auditable_nl2sql.demo --output .local/demo.sqlite3
```

第二条命令会创建新的合成数据库；目标文件已存在时会失败，避免意外覆盖。

当前事实与下一步见 [`docs/status.md`](docs/status.md)。

公开源码：<https://github.com/suuny-ab/auditable-nl2sql-agent>
