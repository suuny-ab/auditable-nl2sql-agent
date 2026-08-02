# Docker 本地启动

仓库根目录的 `compose.yaml` 构建 `deploy/Dockerfile`，并启动只读 API：

```powershell
docker compose up --build --detach --wait
curl.exe --fail --silent --show-error http://127.0.0.1:8000/api/v1/health
curl.exe --fail --silent --show-error http://127.0.0.1:8000/api/v1/runs/container-demo-run
docker compose down
```

镜像使用 hash lock 安装依赖，以 UID/GID `10001:10001` 运行，并在构建阶段调用现有产品代码生成
固定合成业务库与 workflow checkpoint。入口脚本把这两份镜像原件复制到临时 `/tmp` 并设为
`0444`，让 SQLite WAL 可以在同目录创建瞬时共享内存文件，而产品 reader 仍以
`mode=ro + query_only` 打开数据库。Compose 进一步启用只读根文件系统、临时 `/tmp`、
`cap_drop=ALL`、`no-new-privileges` 和回环端口。

本片复用 Traceable 已验证的固定 Python 镜像 digest、多阶段锁依赖、非 root、只读 Compose 和
health gate 姿势。没有复用 Caddy/TLS、production compose、GHCR、release manifest、SSH、数据
卷迁移或部署回滚，因为这些会越过“本地容器化、不部署”的边界。完整复用审查与验收合同见
[`docs/work/docker-compose-readonly-api.md`](../docs/work/docker-compose-readonly-api.md)。
