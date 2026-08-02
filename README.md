# auditable-nl2sql-agent

[![CI](https://github.com/suuny-ab/auditable-nl2sql-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/suuny-ab/auditable-nl2sql-agent/actions/workflows/ci.yml)

一个只使用合成数据的可审计 NL2SQL 作品集项目。当前 LangGraph 工作流可在确定性 SQL stub 与
默认禁用的 DeepSeek SQL generator 之间注入选择：问题经过 schema 读取、SQL 生成和机械只读
执行，形成独立 SQLite checkpoint 与可按 run ID 回查的 JSON trajectory。Provider 模型、action、
结束原因和 token usage 以脱敏回执写入同一 trajectory；执行结果再与问题、SQL、schema 快照及
校验回执绑定为可重算 SHA-256 指纹的 `evidence-v1`，并生成只陈述证据直接支持内容的
`answer-v1`。高行数和写操作查询会在执行前持久化挂起，人工批准仍不能绕过机械只读边界。

首次 20 条固定模型基线为执行成功率 `7/8`、答案正确率 `14/20`、人工介入率 `7/20`；它只代表
冻结合成集上的单次结果，不构成生产稳定性主张。FastAPI 只读服务已提供 health、任务摘要列表和
完整 run/trajectory 回查，并可由 Docker Compose 启动固定合成演示；网页仍待实现。当前回答是
确定性结果投影，
不是 LLM 自由回答；SHA-256 用于稳定绑定和变化检测，不是数字签名，也不证明 SQL 或答案的业务
语义正确。

## 当前目录

```text
api/       Python 产品代码与测试
docs/      当前状态和有界切片合同
evals/     20 条固定合成评测合同与机器校验
web/       最小任务/轨迹页面（待实现）
deploy/    Docker 构建、固定合成 fixture 与部署边界说明
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

## 启动只读 API

下面的业务库与 checkpoint 必须已经存在；服务只读打开二者，缺失时启动失败且不会创建文件。

```powershell
$env:PYTHONPATH = "api/src"
& $python -m auditable_nl2sql.server `
  --business-database .local/demo.sqlite3 `
  --checkpoint-database .local/workflow.sqlite3 `
  --host 127.0.0.1 `
  --port 8000
```

安装项目后也可使用等价入口 `auditable-nl2sql-api`。启动成功后，
`GET http://127.0.0.1:8000/api/v1/health` 返回服务版本和 `read_only=true`；服务不提供 run 创建或
审批接口。

## 从克隆到 Docker 启动

下面是一条完整的本地 PowerShell 命令链。镜像构建期只生成固定合成电商数据库和一个已完成的
`container-demo-run`；运行容器不读取本机数据库、Provider 凭据或真实数据。

```powershell
git clone https://github.com/suuny-ab/auditable-nl2sql-agent.git
Set-Location auditable-nl2sql-agent
docker compose up --build --detach --wait
curl.exe --fail --silent --show-error http://127.0.0.1:8000/api/v1/health
curl.exe --fail --silent --show-error http://127.0.0.1:8000/api/v1/runs/container-demo-run
docker compose logs api
docker compose down
```

服务默认只绑定 `127.0.0.1:8000`。端口被占用时，可在启动前执行
`$env:AUDITABLE_NL2SQL_API_PORT = "18000"`。Compose 运行 API 时使用 UID/GID `10001:10001`、
只读根文件系统、移除全部 Linux capabilities，并把 `/tmp` 设为临时文件系统。这是本地容器化
证据，不是服务器部署、TLS、鉴权或生产可用声明。

只构建镜像而不启动 Compose 时使用：

```powershell
docker build --file deploy/Dockerfile --build-arg VCS_REF=local --tag auditable-nl2sql-api:local .
```

当前事实与下一步见 [`docs/status.md`](docs/status.md)。

公开源码：<https://github.com/suuny-ab/auditable-nl2sql-agent>
