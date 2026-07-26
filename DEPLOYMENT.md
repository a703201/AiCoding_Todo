# 部署运维指南

> 适用于 AiCoding Todo v1.4.0 生产环境部署

---

## 目录

- [快速部署](#快速部署)
- [Docker 架构](#docker-架构)
- [环境变量](#环境变量)
- [Gunicorn 配置](#gunicorn-配置)
- [Nginx 反向代理](#nginx-反向代理)
- [数据库运维](#数据库运维)
- [日志管理](#日志管理)
- [健康检查](#健康检查)
- [备份与恢复](#备份与恢复)
- [性能调优](#性能调优)
- [故障排查](#故障排查)

---

## 快速部署

### 前置要求

- Docker 20.10+
- Docker Compose v1.29+ 或 `docker compose` 插件
- 至少 1GB 可用内存

### 一键部署

```bash
# 1. 克隆仓库
git clone <repo-url>
cd AiCoding_Todo

# 2. 配置环境变量
cp env.example .env
# 编辑 .env，修改 SECRET_KEY、数据库密码等

# 3. 部署
./deploy.sh production
```

部署脚本会自动执行：
1. 依赖检查（Docker + Docker Compose）
2. 环境变量安全检查（SECRET_KEY 强度、FLASK_ENV 验证）
3. 运行测试（确保代码质量）
4. 停止旧服务 → 构建镜像 → 启动服务
5. 等待服务就绪（健康检查轮询，最长 60 秒）
6. 可选执行数据库迁移

### 使用 Makefile

```bash
make build       # 构建 Docker 镜像
make deploy      # 启动所有服务
make stop        # 停止所有服务
make restart     # 重启服务
make logs        # 查看实时日志
make health      # 健康检查 + 服务状态
```

---

## Docker 架构

### 服务拓扑

```
                  Internet
                     │
                     ▼
              ┌─────────────┐
              │   Nginx      │  :80 (反向代理)
              │   Alpine     │
              └──────┬───────┘
                     │
              ┌──────▼───────┐
              │  Flask App   │  :5000 (Gunicorn)
              │  Python 3.9  │
              └──┬────────┬──┘
                 │        │
        ┌────────▼──┐  ┌──▼────────┐
        │ PostgreSQL │  │   Redis   │
        │ 13 Alpine  │  │ 6 Alpine  │
        │   :5432    │  │   :6379   │
        └────────────┘  └───────────┘
```

### 端口映射

| 服务 | 内部端口 | 外部端口 | 说明 |
|------|----------|----------|------|
| Nginx | 80 | `${NGINX_PORT}` | 默认仅 `127.0.0.1:80` |
| Flask App | 5000 | `127.0.0.1:5000` | 仅本地访问 |
| PostgreSQL | 5432 | `127.0.0.1:5432` | 仅本地访问 |
| Redis | 6379 | `127.0.0.1:6379` | 仅本地访问 |

> **安全原则**：所有数据服务端口绑定 `127.0.0.1`，不直接暴露到公网，外部流量必须通过 Nginx。

### 健康检查配置

| 服务 | 检查方式 | 间隔 | 超时 | 重试 |
|------|----------|------|------|------|
| todo-app | `curl /health` | 30s | 10s | 3 |
| db | `pg_isready` | 10s | 5s | 10 |
| redis | `redis-cli ping` | 10s | 5s | 5 |

### Redis 内存策略

```yaml
command: redis-server --appendonly yes --maxmemory 64mb --maxmemory-policy allkeys-lru
```

- **AOF 持久化**：`appendonly yes` 保证数据安全
- **最大内存**：64MB（可通过环境变量调整）
- **淘汰策略**：`allkeys-lru`（内存不足时淘汰最少使用的 key）

---

## 环境变量

完整环境变量列表参见 `env.example`，关键变量说明：

### 应用核心

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `FLASK_ENV` | `production` | 环境模式，生产必须为 `production` |
| `SECRET_KEY` | — | **必须修改**，生成命令见下方 |
| `CORS_ORIGINS` | `*` | 允许的跨域来源 |

### 数据库

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql://todo_user:todo_password@db:5432/todo_db` | 数据库连接串 |
| `DB_POOL_SIZE` | `10` | 连接池大小 |
| `DB_MAX_OVERFLOW` | `20` | 连接池溢出上限 |
| `DB_POOL_TIMEOUT` | `30` | 获取连接超时（秒） |
| `DB_POOL_RECYCLE` | `3600` | 连接回收时间（秒） |

### Redis 缓存

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `REDIS_URL` | `redis://redis:6379/0` | Redis 连接串 |

### 服务器

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GUNICORN_WORKERS` | `CPU*2+1` | Worker 进程数 |
| `GUNICORN_THREADS` | `2` | 每个 Worker 的线程数 |
| `GUNICORN_TIMEOUT` | `30` | 请求超时（秒） |
| `GUNICORN_MAX_REQUESTS` | `10000` | Worker 最大处理请求数（防内存泄漏） |

### 监控阈值

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HEALTH_DISK_THRESHOLD` | `90` | 磁盘使用率告警阈值（%） |
| `HEALTH_MEM_THRESHOLD` | `95` | 内存使用率告警阈值（%） |

### 生成安全密钥

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

---

## Gunicorn 配置

配置文件：`gunicorn.conf.py`

### 关键参数

```python
bind = "0.0.0.0:5000"
workers = CPU * 2 + 1          # 可通过 GUNICORN_WORKERS 覆盖
worker_class = "sync"           # 同步模式
threads = 2                     # 每个 worker 的线程数
timeout = 30                    # 请求超时
max_requests = 10000            # 防止内存泄漏，达到后自动重启 worker
max_requests_jitter = 1000      # 随机抖动，避免同时重启
keepalive = 2                   # Keep-Alive 超时
```

### Worker 数量建议

| CPU 核心 | 建议 Worker 数 | 适用场景 |
|----------|---------------|----------|
| 1 | 3 | 开发 / 小型部署 |
| 2 | 5 | 中等负载 |
| 4 | 9 | 生产环境 |
| 8+ | 9-17 | 高并发 |

> 公式：`workers = CPU * 2 + 1`，IO 密集型可适当增加。

### 信号管理

```bash
# 优雅重启（不中断服务）
kill -HUP $(cat /tmp/gunicorn.pid)

# 优雅停止
kill -TERM $(cat /tmp/gunicorn.pid)
```

---

## Nginx 反向代理

配置文件：`nginx.conf`

### 速率限制

| 区域 | 限制 | 突发 | 适用路径 |
|------|------|------|----------|
| `api_limit` | 10 r/s | 20 | `/api/*` |
| `page_limit` | 20 r/s | 30 | `/` |
| `login_limit` | 5 r/m | — | 预留登录 |

超限时返回 `429 Too Many Requests`：
```json
{"error": "请求过于频繁，请稍后再试", "retry_after": 1}
```

### 安全头

| 响应头 | 值 | 说明 |
|--------|-----|------|
| `X-Frame-Options` | `DENY` | 禁止被嵌入 iframe |
| `X-Content-Type-Options` | `nosniff` | 禁止 MIME 嗅探 |
| `X-XSS-Protection` | `1; mode=block` | XSS 过滤器 |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | 控制 Referer |
| `Permissions-Policy` | 禁用摄像头/麦克风/定位 | 功能权限 |
| `CSP` | 仅允许 CDN 脚本/样式 | 内容安全策略 |

### 指标端点保护

`/metrics` 端点仅允许以下 IP 访问：
- `127.0.0.1`（本地）
- `172.16.0.0/12`（Docker 内部网络）
- `10.0.0.0/8`（私有网络）

### SSL/TLS 配置

`nginx.conf` 中已包含 SSL 配置模板（默认注释），启用步骤：

1. 获取 SSL 证书（Let's Encrypt 推荐）
2. 将证书放到 Nginx 容器的 `/etc/nginx/ssl/` 目录
3. 取消注释 SSL server block
4. 取消注释 HTTP → HTTPS 重定向

### Gzip 压缩

已启用 Gzip 压缩（级别 6），压缩以下类型：
- `text/*`（HTML/CSS/JS/XML）
- `application/json`、`application/javascript`
- `image/svg+xml`

---

## 数据库运维

### 迁移管理

使用 Alembic 管理数据库变更，**以迁移文件为准**。

```bash
# 执行迁移
make upgrade
# 或
docker compose exec todo-app flask db upgrade

# 回滚
make downgrade

# 查看迁移历史
docker compose exec todo-app flask db history

# 查看当前版本
docker compose exec todo-app flask db current
```

### 直接连接数据库

```bash
make db-shell
# 或
docker compose exec db psql -U todo_user -d todo_db
```

### 表结构

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| `todos` | 待办事项 | id, title, completed, priority, category, due_date |
| `tags` | 标签 | id, name (UNIQUE), color |
| `todo_tags` | 多对多关联 | todo_id, tag_id (复合 PK) |

### 索引

`todos` 表共 7 个索引：`title`、`completed`、`priority`、`due_date`、`created_at`、`(completed, priority)`、`(category, priority)`

---

## 日志管理

### 日志类型

| 日志 | 路径 | 格式 | 轮转 |
|------|------|------|------|
| 应用日志 | `logs/app-*.log` | 结构化 JSON | 按日轮转，保留 30 天 |
| Gunicorn 访问 | `logs/gunicorn-access.log` | 自定义格式 | — |
| Gunicorn 错误 | `logs/gunicorn-error.log` | — | — |
| Nginx 访问 | `/var/log/nginx/todo_access.log` | 标准 | — |
| Nginx 错误 | `/var/log/nginx/todo_error.log` | — | — |

### 日志级别

通过 `LOG_LEVEL` 环境变量控制：`DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`

### 查看日志

```bash
# 所有服务实时日志
make logs

# 仅应用日志
docker compose logs -f todo-app

# 查看最近 100 行
docker compose logs --tail=100 todo-app
```

### JSON 日志格式

```json
{
  "timestamp": "2026-07-26T10:30:00.123Z",
  "level": "INFO",
  "name": "app.services.todo_service",
  "message": "创建待办事项: id=42",
  "module": "todo_service",
  "funcName": "create_todo",
  "lineno": 147
}
```

---

## 健康检查

### HTTP 端点

```bash
curl http://localhost:5000/health
```

**正常响应**（200）：
```json
{
  "status": "ok",
  "database": "ok",
  "redis": "ok",
  "disk_usage_percent": 45.2,
  "memory_usage_percent": 62.1,
  "total_todos": 128,
  "total_tags": 15
}
```

**降级响应**（503）：
```json
{
  "status": "degraded",
  "database": "error",
  "redis": "ok",
  "disk_usage_percent": 92.5,
  "memory_usage_percent": 68.3,
  "total_todos": 128,
  "total_tags": 15
}
```

### 降级触发条件

| 条件 | 默认阈值 | 环境变量 |
|------|----------|----------|
| 数据库连接失败 | — | — |
| 磁盘使用率过高 | > 90% | `HEALTH_DISK_THRESHOLD` |
| 内存使用率过高 | > 95% | `HEALTH_MEM_THRESHOLD` |

> Redis 不可用**不会**触发降级，因为应用有优雅降级机制。

### Nagios 兼容检查脚本

```bash
./scripts/healthcheck.sh [host] [port] [timeout]
```

退出码：
- `0` — OK（服务正常）
- `1` — WARNING（数据库异常）
- `2` — CRITICAL（无法连接或服务异常）

---

## 备份与恢复

### 自动备份

```bash
make backup
# 或
./scripts/backup.sh
```

备份文件：`backups/todo_backup_YYYYMMDD_HHMMSS.sql.gz`

- 自动压缩（gzip）
- 默认保留 30 天（通过 `BACKUP_RETENTION_DAYS` 配置）
- 自动清理过期备份

### 恢复数据

```bash
make restore
# 按提示输入备份文件路径

# 或手动恢复
gunzip -c backups/todo_backup_20260726_103000.sql.gz | \
  docker compose exec -T db psql -U todo_user -d todo_db
```

### 定时备份（Cron）

```bash
# 每天凌晨 2 点备份
0 2 * * * cd /path/to/AiCoding_Todo && ./scripts/backup.sh >> backups/cron.log 2>&1
```

---

## 性能调优

### 连接池优化

| 参数 | 建议值 | 适用场景 |
|------|--------|----------|
| `DB_POOL_SIZE` | 5-20 | 并发连接数 |
| `DB_MAX_OVERFLOW` | pool_size * 2 | 突发流量 |
| `DB_POOL_RECYCLE` | 3600 | 防止连接过期 |

### Worker 调优

- **IO 密集型**（数据库操作多）：增加 `threads` 到 4
- **CPU 密集型**：增加 `workers`，保持 `threads=1`

### Redis 缓存

- 默认 TTL 30 秒，可通过 `CACHE_TTL` 调整
- 缓存命中率监控：`redis-cli INFO stats | grep keyspace`

### 数据库索引

已有的索引覆盖了所有常见查询路径。如需添加新索引：

```sql
CREATE INDEX CONCURRENTLY idx_name ON todos(column);
```

---

## 故障排查

### 服务无法启动

```bash
# 1. 查看服务状态
make health

# 2. 查看日志
docker compose logs todo-app | tail -50

# 3. 常见问题：
# - 端口被占用 → 修改 docker-compose.yml 中的端口映射
# - 数据库未就绪 → 增加 healthcheck retries
# - 磁盘空间不足 → docker system prune -a
```

### 数据库连接失败

```bash
# 检查数据库状态
docker compose exec db pg_isready -U todo_user -d todo_db

# 检查连接池
docker compose exec todo-app python -c "
from app import create_app
app = create_app('production')
with app.app_context():
    from app.extensions import db
    db.session.execute('SELECT 1')
    print('OK')
"
```

### Redis 不可用

应用自动降级，不影响核心功能。检查：

```bash
docker compose exec redis redis-cli ping
```

### 内存泄漏

```bash
# 查看资源使用
make stats

# 查看 worker 重启情况
docker compose logs todo-app | grep "Worker"
```

如果 `max_requests` 触发频繁重启，可调高该值或排查代码中的内存泄漏。

### 常用运维命令

```bash
# 查看所有容器状态
docker compose ps

# 进入应用容器
make shell

# 进入 Redis CLI
make redis-cli

# 重启单个服务
docker compose restart todo-app

# 完全重建
docker compose down -v && docker compose up -d --build
```
