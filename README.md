# auditable-nl2sql-agent

[![CI](https://github.com/suuny-ab/auditable-nl2sql-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/suuny-ab/auditable-nl2sql-agent/actions/workflows/ci.yml)

一个只使用合成数据的可审计 NL2SQL 作品集项目。当前 LangGraph 工作流可在确定性 SQL stub 与
默认禁用的 DeepSeek SQL generator 之间注入选择：问题经过 schema 读取、SQL 生成和机械只读
执行，形成独立 SQLite checkpoint 与可按 run ID 回查的 JSON trajectory。Provider 模型、action、
结束原因和 token usage 以脱敏回执写入同一 trajectory；执行结果再与问题、SQL、schema 快照及
校验回执绑定为可重算 SHA-256 指纹的 `evidence-v1`，并生成只陈述证据直接支持内容的
`answer-v1`。高行数和写操作查询会在执行前持久化挂起，人工批准仍不能绕过机械只读边界。

DeepSeek adapter 已通过一条真实收入查询和一条删除请求的最小冒烟，但尚未运行 20 条模型评测，
不构成正确率或生产稳定性主张。默认工作流仍使用可重复的 SQL stub；API、网页、模型评测运行和
Docker 仍待实现。当前回答是确定性结果投影，不是 LLM 自由回答；SHA-256 用于稳定绑定和变化
检测，不是数字签名，也不证明 SQL 或答案的业务语义正确。

## 当前目录

```text
api/       Python 产品代码与测试
docs/      当前状态和有界切片合同
evals/     20 条固定合成评测合同与机器校验
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
