# auditable-nl2sql-agent

[![CI](https://github.com/suuny-ab/auditable-nl2sql-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/suuny-ab/auditable-nl2sql-agent/actions/workflows/ci.yml)

一个只使用合成数据的可审计 NL2SQL 作品集项目。当前已具备确定性离线 LangGraph 工作流：
固定问题经过 schema 读取、SQL stub、机械只读执行，形成独立 SQLite checkpoint 和可按 run ID
回查的 JSON trajectory。执行结果通过结构和截断校验后，会与问题、SQL、schema 快照及校验
回执绑定为可重算 SHA-256 指纹的 `evidence-v1`，再生成只陈述证据直接支持内容并带精确来源
引用的 `answer-v1`。高行数和写操作查询会在执行前持久化挂起，可使用同一 run ID 在另一进程
批准或拒绝；批准仍不能绕过机械只读边界。

当前 SQL stub 只是可重复的工作流替身，不构成真实 NL2SQL 能力或正确率主张。真实模型、
业务语义生成、API、网页、评测和 Docker 仍待实现。当前回答是确定性结果投影，不是 LLM
回答；SHA-256 用于稳定绑定和变化检测，不是数字签名，也不证明 SQL 或答案的业务语义正确。

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
$python = ".venv\Scripts\python.exe"
python -m venv .venv
& $python -m pip install --disable-pip-version-check --no-deps --require-hashes --requirement api/requirements-base.lock
$env:PYTHONPATH = "api/src"
& $python -m unittest discover -s api/tests -p "test_*.py" -v
& $python -m auditable_nl2sql.demo --output .local/demo.sqlite3
```

第二条命令会创建新的合成数据库；目标文件已存在时会失败，避免意外覆盖。

当前事实与下一步见 [`docs/status.md`](docs/status.md)。

公开源码：<https://github.com/suuny-ab/auditable-nl2sql-agent>
