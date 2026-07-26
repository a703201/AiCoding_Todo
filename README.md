# 待办事项应用 (AiCoding Todo)

> **实训项目** | 全栈 Web 开发综合实训 — Flask + PostgreSQL + Redis + Docker + Nginx

---

## 项目简介

本项目是一个功能完整的**待办事项（Todo）管理应用**，作为 **AiCoding 实训课程**的综合实践项目。涵盖从需求分析、数据库设计、后端 API 开发、单元测试、容器化部署到生产环境运维的完整软件开发生命周期。

### 实训目标

- 掌握 Flask Web 框架的工程化实践
- 理解 RESTful API 设计规范
- 掌握关系型数据库设计与 SQLAlchemy ORM
- 实践测试驱动开发（TDD）与单元测试编写
- 学习 Docker 容器化与多服务编排
- 了解生产环境部署（Gunicorn + Nginx + PostgreSQL）
- 熟悉 Redis 缓存策略与 Prometheus 监控

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **Web 框架** | Flask 2.3 + Jinja2 模板 |
| **数据库** | PostgreSQL 13（生产） / SQLite（测试） |
| **ORM** | Flask-SQLAlchemy + Alembic 迁移 |
| **缓存** | Redis 6（旁路缓存模式） |
| **Web 服务器** | Gunicorn（多 worker + 多线程） |
| **反向代理** | Nginx（速率限制 + 安全头 + SSL） |
| **测试** | pytest + pytest-cov（覆盖率 84.6%） |
| **监控** | Prometheus 指标 + 健康检查端点 |
| **容器化** | Docker + Docker Compose |
| **日志** | 结构化 JSON 日志 + 按日期滚动 |

---

## 项目结构

```
AiCoding_Todo/
├── app.py                    # 应用主入口（应用工厂模式）
├── gunicorn.conf.py          # Gunicorn 生产配置
├── requirements.txt          # Python 依赖
├── Dockerfile                # Docker 镜像构建
├── docker-compose.yml        # 多服务编排（app + DB + Redis + Nginx）
├── nginx.conf                # Nginx 反向代理配置
├── Makefile                  # 快捷命令集合
├── env.example               # 环境变量模板
├── pytest.ini                # pytest 配置
├── .coveragerc               # 覆盖率配置
│
├── migrations/               # Alembic 数据库迁移
│   ├── versions/
│   │   ├── 001_initial_schema.py
│   │   └── 002_add_tags.py
│   └── env.py
│
├── templates/
│   └── index.html            # 前端页面
│
├── tests/                    # 单元测试（111 个用例）
│   ├── conftest.py           # 集中式 Fixture + Mock
│   ├── test_app.py           # 核心功能测试（93 个）
│   └── test_mock.py          # Mock 与并发测试（18 个）
│
├── scripts/
│   ├── healthcheck.sh        # 健康检查脚本
│   └── backup.sh             # 数据库备份脚本
│
├── deploy.sh                 # 一键部署脚本
├── startup.sh                # 容器启动脚本
└── run_tests.sh              # 测试运行脚本
```

---

## 快速开始

### 前置要求

- Python 3.9+
- Docker & Docker Compose（用于生产部署）
- Git

### 本地开发

```bash
# 1. 克隆仓库
git clone https://github.com/a703201/AiCoding_Todo.git
cd AiCoding_Todo

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp env.example .env
# 编辑 .env，设置 SECRET_KEY 等

# 4. 初始化数据库（SQLite 开发模式）
flask db upgrade

# 5. 启动开发服务器
python app.py
# 访问 http://localhost:5000
```

### Docker 部署

```bash
# 一键部署
./deploy.sh production

# 或使用 Makefile
make build    # 构建镜像
make deploy   # 启动所有服务
make health   # 健康检查
```

### 访问地址

| 服务 | 地址 |
|------|------|
| 应用主页 | http://localhost:5000 |
| API 接口 | http://localhost:5000/api/ |
| 健康检查 | http://localhost:5000/health |
| 监控指标 | http://localhost:5000/metrics |
| Nginx 代理 | http://localhost:80 |

> ⚠️ **安全提醒**：`docker-compose.yml` 中的数据库密码、Redis 连接和 `SECRET_KEY` 均为默认值，生产部署前请通过 `.env` 文件覆盖。参考 `env.example` 中的环境变量模板。

---

## API 接口文档

### 待办事项 (Todos)

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/todos` | 获取列表（支持分页、搜索、筛选、排序） |
| `POST` | `/api/todos` | 创建待办事项 |
| `GET` | `/api/todos/<id>` | 获取单个待办 |
| `PUT` | `/api/todos/<id>` | 更新待办事项 |
| `DELETE` | `/api/todos/<id>` | 删除待办事项 |
| `POST` | `/api/todos/<id>/toggle` | 切换完成状态 |
| `POST` | `/api/todos/batch/delete-completed` | 批量删除已完成 |
| `GET` | `/api/stats` | 统计摘要 |
| `GET` | `/api/stats/dashboard` | 仪表盘数据 |

### 标签 (Tags)

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/tags` | 获取标签列表 |
| `POST` | `/api/tags` | 创建标签 |
| `GET` | `/api/tags/<id>` | 获取单个标签 |
| `PUT` | `/api/tags/<id>` | 更新标签 |
| `DELETE` | `/api/tags/<id>` | 删除标签 |

### 查询参数

```
GET /api/todos?page=1&per_page=20&search=关键词&priority=high&category=work&sort_by=created_at&sort_order=desc
```

---

## 测试

```bash
# 运行全部测试
make test

# 覆盖率报告（HTML）
make coverage

# 测试特定模块
pytest tests/ -v -k "TestTagCRUD"

# 带覆盖率 + XML 输出
make test-all
```

**测试统计：**

| 类别 | 测试数 | 覆盖内容 |
|------|--------|----------|
| 待办 CRUD | 45 | 创建、查询、更新、删除、切换 |
| 搜索分页 | 14 | 搜索、筛选、排序、分页 |
| 标签系统 | 10 | 标签 CRUD + 多对多关联 |
| 统计分析 | 3 | stats + dashboard + 标签频率 |
| 数据模型 | 6 | 序列化、默认值、关系、约束 |
| 事务安全 | 4 | 回滚、批量、savepoint |
| Mock 测试 | 10 | Redis 缓存命中/未命中/降级 |
| 并发测试 | 3 | 批量创建、反复切换 |
| 监控指标 | 7 | /health 增强、/metrics |
| 部署配置 | 4 | 工厂模式、日志、错误处理 |
| 其他 | 5 | 集成测试、边界值、HTTP 状态码 |
| **总计** | **111** | **覆盖率 84.6%** |

---

## 架构设计

### 系统架构

```
                    ┌─────────┐
                    │  Nginx  │  反向代理 + 速率限制
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │ Gunicorn│  多 worker 进程
                    └────┬────┘
                         │
            ┌────────────┼────────────┐
            │            │            │
       ┌────▼───┐   ┌───▼────┐  ┌────▼───┐
       │  Flask  │   │ Redis  │  │  Logs  │
       │   App   │   │  Cache │  │  (JSON)│
       └────┬────┘   └────────┘  └────────┘
            │
       ┌────▼────┐
       │PostgreSQL│  持久化存储
       └─────────┘
```

### 数据模型

```
┌─────────────┐       ┌──────────────────┐       ┌─────────────┐
│    Todo     │       │  todo_tag_assoc  │       │     Tag     │
├─────────────┤       ├──────────────────┤       ├─────────────┤
│ id (PK)     │──1:N──│ todo_id (FK)     │──N:1──│ id (PK)     │
│ title       │       │ tag_id (FK)      │       │ name (UNIQUE)│
│ description │       └──────────────────┘       │ color       │
│ priority    │                                  └─────────────┘
│ category    │
│ due_date    │
│ completed   │
│ created_at  │
│ updated_at  │
└─────────────┘
```

### 缓存策略

采用**旁路缓存（Cache-Aside）**模式：
- 读取：先查 Redis → 命中返回 / 未命中查 DB 并回写缓存
- 写入：更新 DB → 删除相关缓存
- 降级：Redis 不可用时直接读写数据库，零影响

---

## 部署运维

### Makefile 常用命令

```bash
make help        # 查看所有命令
make test        # 运行测试
make coverage    # 测试覆盖率
make build       # 构建 Docker 镜像
make deploy      # 生产环境部署
make logs        # 查看日志
make health      # 健康检查
make backup      # 数据库备份
make restore     # 数据库恢复
make db-shell    # 数据库命令行
make redis-cli   # Redis 命令行
```

### 健康检查

```bash
curl http://localhost:5000/health
```

返回示例：
```json
{
  "status": "ok",
  "database": "ok",
  "redis": "available",
  "disk_usage_percent": 12.5,
  "memory_usage_percent": 35.2,
  "total_todos": 42,
  "total_tags": 8
}
```

### Prometheus 指标

```bash
curl http://localhost:5000/metrics
```

关键指标：`todo_total`、`todo_completed`、`todo_pending`、`todo_by_priority`、`redis_available`

---

## 安全特性

| 特性 | 实现 |
|------|------|
| 速率限制 | Nginx `limit_req`（API 10r/s） |
| 安全头 | X-Frame-Options、XSS Protection、CSP、HSTS |
| 输入校验 | 服务端参数验证（标题必填、枚举校验） |
| SQL 注入防护 | SQLAlchemy ORM 参数化查询 |
| CORS 配置 | Flask-CORS 白名单控制 |
| 非 root 运行 | Docker 容器使用非特权用户 |

---

## 实训学习要点

本实训项目涵盖以下核心技能：

1. **Web 开发基础**
   - Flask 应用工厂模式
   - RESTful API 设计
   - Jinja2 模板渲染
   - Flask 扩展生态（SQLAlchemy / Migrate / CORS）

2. **数据库设计与操作**
   - 关系型数据建模（一对多、多对多）
   - Alembic 数据库迁移管理（正式环境以迁移文件为准）
   - `init.sql` 仅用于 Docker 首次初始化，需与 Alembic 迁移保持同步
   - 复杂查询（聚合、分组、JOIN、窗口函数）
   - 索引优化与 SQL 调优
   - 跨数据库方言差异（SQLite vs PostgreSQL，见 `sql_practice.sql`）

3. **测试驱动开发**
   - pytest Fixture 与参数化测试
   - Mock 对象与依赖隔离
   - 测试覆盖率分析与提升
   - 并发安全测试

4. **DevOps 与部署**
   - Docker 多阶段构建
   - Docker Compose 多服务编排
   - Gunicorn 生产配置优化
   - Nginx 反向代理与安全加固

5. **监控与运维**
   - 结构化 JSON 日志
   - 健康检查端点（DB / Redis / 磁盘 / 内存）
   - Prometheus 指标暴露
   - 数据库备份与恢复

---

## 许可证

本项目为 **AiCoding 实训教学项目**，仅供学习参考。
