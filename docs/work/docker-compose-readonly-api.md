# DOCKER-COMPOSE-READONLY-API-016

## Goal

让公开仓库可以用一条 Docker Compose 命令构建并启动只读 API；容器内只使用预生成的合成数据，
health 与既有 run 回查均可验证。

## Non-goals

- 不部署到服务器，不配置域名、TLS、Caddy、GHCR 发布或自动部署。
- 不启用或调用 Provider，不读取凭据，不增加代码层费用逻辑。
- 不做网页、鉴权、生产数据卷迁移或真实数据接入。
- 不修改 `api/src` 产品代码、HTTP 合同、workflow 合同或现有评测口径。
- 不把本地容器通过结果表述为生产可用、公开上线或身份权限已完成。

## Acceptance criteria

1. **WHEN** 在仓库根目录执行 README 的 `docker compose up --build --detach --wait`，**THEN**
   镜像从固定 Python 基础镜像和 hash lock 构建成功，API 进程 UID/GID 为 `10001:10001`。
2. **WHEN** Compose 报告服务 healthy，**THEN** `GET /api/v1/health` 返回
   `health-v1 / status=ok / read_only=true`。
3. **WHEN** 请求 `GET /api/v1/runs/container-demo-run`，**THEN** 返回已完成的
   `run-record-v5`，证明镜像只包含明确标注的固定合成演示数据。
4. **WHEN** 连续执行 health、run list/detail 与拒绝请求，**THEN** 容器内业务库和 checkpoint
   的 SHA-256 前后不变，`POST` 请求返回 `405`。
5. **WHEN** 检查 Compose 运行合同，**THEN** API 只绑定 `127.0.0.1`，根文件系统只读，
   `cap_drop=ALL`、`no-new-privileges` 与临时 `/tmp` 生效。
6. **WHEN** 执行容器外 Python 3.13 全量测试，**THEN** 所有产品与部署合同测试通过。
7. **WHEN** Pull Request CI 运行，**THEN** Python job 与 Compose build/health/run-query job
   都必须成功，容器 job 不调用 Provider、不发布镜像、不部署。
8. **WHEN** 新读者查看 README 与 `deploy/README.md`，**THEN** 能找到从克隆、进入目录到启动、
   验证、查看日志和停止服务的完整命令链。
9. **WHEN** 复核版本差异，**THEN** `api/src`、Provider 开关、凭据、安全边界和费用逻辑均未改变。

## Rollback

回滚本切片的单一提交；这会移除 Dockerfile、Compose、构建期合成 fixture、容器合同测试、CI
容器 job 和对应文档，不改变已合并的产品代码或数据合同。

## 本场规则复述

- 只使用明确标注的合成数据；镜像不得包含真实数据库、凭据、Provider 回执或本地 `.local`。
- 本切片只交付本地容器化闭环；服务器部署、公开发布、鉴权和网页均不顺手实现。
- 完成前必须有真实镜像构建、Compose health、run 回查、哈希不变和全量测试输出；远端 CI
  绿色不能替代本地容器验收。

## Traceable 复用审查

### 复用

- 复用 `python:3.13-slim-bookworm` 的 digest 固定方式、多阶段 hash-lock 安装和不把构建工具带入
  运行层的做法。
- 复用 UID/GID `10001:10001` 非 root 运行、镜像内 `HEALTHCHECK`、Compose 回环端口、
  `read_only`、临时 `/tmp`、`cap_drop=ALL`、`no-new-privileges` 与 `--wait` 健康门姿势。
- 复用 CI 中“构建 → 等待 health → 校验 JSON 合同 → 查询业务接口 → 失败时输出日志”的证据链。

### 不复用

- 不复用 Caddy/TLS、production compose、GHCR 摘要发布、release manifest、SSH、数据卷迁移、
  回滚编排或部署 guard；这些属于下一片服务器部署与公开发布边界。
- 不复用 Traceable 的 root 数据卷初始化器：本项目当前演示数据库在镜像构建期由现有产品代码
  生成；入口层只把数据库复制到临时 tmpfs 并设为 `0444`，供 SQLite WAL 创建瞬时共享内存文件，
  产品 reader 仍用 `mode=ro + query_only`，且无需持久化写卷。
- 不复制 Traceable 的 Provider/live 镜像、BGE 模型或 Web 服务；本片只有确定性只读 API。

## Evidence

- Docker `29.5.3` / Compose `5.1.4` / Linux x86_64：固定 Python 3.13 digest 与 hash lock 构建
  `sha256:8f42a490…f0613b` 成功，镜像配置用户为 `10001:10001`。
- `docker compose up --build --detach --wait` 成功；health 精确合同、run list、
  `container-demo-run / completed / run-record-v5` 和 POST `405` 全部通过。
- 容器身份 `10001:10001`；数据库模式 `0444:10001:10001`；根文件系统写入失败；
  `read_only`、`cap_drop=ALL`、`no-new-privileges`、tmpfs 与 `127.0.0.1:8000` 均由
  `docker inspect`/Compose 实测确认。
- health、list、detail 与拒绝请求前后，两份运行时 SQLite 的 SHA-256 完全相同。
- 初次启动复现 WAL checkpoint 在只读镜像目录无法创建共享内存文件；隔离对照证明复制到 tmpfs
  后可由同一 `mode=ro + query_only` reader 读取，因此只调整容器入口层，`api/src` 保持零差异。
- Python `3.13.12` 新增 2 项容器合同、全量 55 项通过；`compileall`、`pip check`、Compose
  解析、差异、凭据模式、`.local` 与产品依赖方向检查通过。
- Provider 调用、凭据读取、token 消耗、费用、服务器写入、镜像发布与部署均为 `0`；远端 CI
  尚待 Draft PR 后验证，不把本地绿色写成远端证据。
- 本地提交 `1316421ce457e7718c508c2b2423489869f67b6c` 已生成；GitHub 账号认证有效，但 OAuth token
  缺少修改 `.github/workflows/ci.yml` 所需的 `workflow` scope，首次 push 被远端拒绝。远端分支
  与 Draft PR 均未创建，需凭据 scope 恢复后从该精确提交继续。
