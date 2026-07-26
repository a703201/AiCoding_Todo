# 待办事项应用 (AiCoding Todo)

> **实训项目** | 全栈 Web 开发综合实训 — Flask + PostgreSQL + Redis + Docker + Nginx

---

## 文档导航

| 文档 | 说明 |
|------|------|
| [README.md](README.md) | 项目概览、快速开始、架构说明（本文档） |
| [API.md](API.md) | 完整 API 接口文档（20 个端点） |
| [DEPLOYMENT.md](DEPLOYMENT.md) | 部署运维指南（Docker / Nginx / 备份 / 故障排查） |
| [DEVELOPMENT.md](DEVELOPMENT.md) | 开发指南（项目结构 / 测试 / 迁移 / 调试） |
| [CHANGELOG.md](CHANGELOG.md) | 版本更新日志 |

---

## 项目简介

本项目是一个功能完整的**待办事项（Todo）管理应用**，作为 **AiCoding 实训课程**的综合实践项目。涵盖从需求分析、数据库设计、后端 API 开发、单元测试、容器化部署到生产环境运维的完整软件开发生命周期。

### 实训目标

- 掌握 Flask Web 框架的工程化实践与模块化分层架构
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
| **架构模式** | 应用工厂模式 + Blueprint + Service 层分层 |
| **数据库** | PostgreSQL 13（生产） / SQLite（测试/开发） |
| **ORM** | Flask-SQLAlchemy 3.0 + Alembic 迁移管理 |
| **缓存** | Redis 6（Cache-Aside 模式 + 优雅降级） |
| **Web 服务器** | Gunicorn（多 worker + 多线程） |
| **反向代理** | Nginx（速率限制 + 安全头 + SSL 模板） |
| **测试** | pytest + pytest-cov（193 用例，覆盖率 91%） |
| **监控** | Prometheus 指标 + 增强健康检查端点 |
| **日志** | 结构化 JSON 日志 + 按日轮转（30 天保留） |
| **容器化** | Docker 多阶段构建 + Docker Compose 四服务编排 |

---

## 项目结构

```
AiCoding_Todo/
├── app/                          # 应用核心包（大厂标准分层架构）
│   ├── __init__.py               # create_app() 应用工厂 + 蓝图注册
│   ├── config.py                 # 配置类继承体系（Base/Dev/Test/Prod）
│   ├── extensions.py             # db/migrate/redis 扩展（延迟绑定）
│   ├── exceptions.py             # 自定义异常层次（AppException → NotFound/Conflict/Validation/Business）
│   ├── api/                      # API 路由层（Flask Blueprint）
│   │   ├── __init__.py           # 蓝图汇总导出
│   │   ├── health.py             # 首页 + 健康检查 + Prometheus 指标
│   │   ├── todos.py              # Todo CRUD + 标签关联操作（10 个端点）
│   │   ├── tags.py               # Tag CRUD（5 个端点）
│   │   └── stats.py              # 统计 + 仪表盘（2 个端点）
│   ├── services/                 # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── todo_service.py       # Todo 业务逻辑（CRUD/搜索/分页/统计/健康/指标）
│   │   └── tag_service.py        # Tag 业务逻辑（CRUD + 关联操作）
│   ├── repositories/             # 数据访问层（Repository 模式）
│   │   ├── __init__.py           # TodoRepository + TagRepository（纯静态方法）
│   ├── schemas/                  # Schema/DTO 层（dataclass）
│   │   ├── __init__.py           # 6 个 Schema 集中导出
│   │   ├── todo.py               # TodoCreateSchema / TodoUpdateSchema / TodoOutSchema
│   │   └── tag.py                # TagCreateSchema / TagUpdateSchema / TagOutSchema
│   ├── models/                   # 数据模型层
│   │   ├── __init__.py           # 模型集中导出
│   │   ├── todo.py               # Todo ORM（8 字段 + 7 索引 + M:N 关联）
│   │   └── tag.py                # Tag ORM + todo_tags 关联表
│   ├── utils/                    # 工具层
│   │   ├── __init__.py
│   │   ├── validators.py         # 统一输入校验（Todo/日期/颜色/标签名/LIKE 转义）
│   │   ├── cache.py              # Redis Cache-Aside 辅助
│   │   └── logging.py            # 结构化日志配置
│   └── errors/                   # 错误处理
│       ├── __init__.py
│       └── handlers.py           # 全局错误处理器（400/404/405/500 + AppException）
│
├── app.py                        # 向后兼容入口（Gunicorn + 开发运行）
├── gunicorn.conf.py              # Gunicorn 生产配置（多 worker/线程/超时/日志）
├── requirements.txt              # Python 依赖
├── Dockerfile                    # Docker 多阶段构建（非 root 运行）
├── docker-compose.yml            # 四服务编排（app + PostgreSQL + Redis + Nginx）
├── nginx.conf                    # Nginx 反向代理 + 速率限制 + 安全头 + SSL 模板
├── Makefile                      # 快捷命令集合（开发/测试/部署/运维）
├── env.example                   # 环境变量模板（含注释说明）
├── pytest.ini                    # pytest 配置（80% 覆盖率门槛）
├── .coveragerc                   # 覆盖率排除配置
├── .dockerignore                 # Docker 构建排除
├── .gitignore                    # Git 排除规则
│
├── migrations/                   # Alembic 数据库迁移
│   ├── alembic.ini               # Alembic 配置文件
│   ├── env.py                    # 迁移环境（在线/离线模式）
│   ├── script.py.mako            # 迁移脚本模板
│   └── versions/
│       ├── 001_initial_schema.py # 初始迁移：todos 表 + 7 个索引
│       └── 002_add_tags.py       # 标签迁移：tags 表 + 关联表 + 数据迁移
│
├── templates/
│   └── index.html                # 前端单页应用（Bootstrap 5 + TodoApp 类）
│
├── tests/                        # 测试套件（193 个用例）
│   ├── conftest.py               # 集中式 Fixture + Mock Redis + 辅助函数
│   ├── test_app.py               # 核心功能测试（15 测试类，93 用例）
│   ├── test_mock.py              # Mock 与并发测试（5 测试类，18 用例）
│   └── test_coverage_supplement.py  # 覆盖率补充测试（82 用例）
│
├── scripts/
│   ├── healthcheck.sh            # Nagios 兼容健康检查脚本
│   └── backup.sh                 # PostgreSQL 备份 + 压缩 + 清理
│
├── deploy.sh                     # 一键部署脚本（含安全检查和环境验证）
├── startup.sh                    # 容器启动脚本（等待依赖 → 迁移 → 启动）
├── run_tests.sh                  # 测试运行脚本（支持覆盖率/并行/watch）
├── migrate_db.py                 # 数据库迁移 CLI 管理脚本
│
└── sql_practice.sql              # SQL 练习（基础/聚合/关联/CTE/事务/窗口函数）
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
# 一键部署（含安全检查）
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

> ⚠️ **安全提醒**：`docker-compose.yml` 中的数据库密码、Redis 连接和 `SECRET_KEY` 均为默认值，生产部署前请通过 `.env` 文件覆盖。参考 `env.example` 中的环境变量模板。部署脚本会在生产环境下自动检查密钥安全性。

---

## API 接口文档

### 待办事项 (Todos)

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/todos` | 获取列表（支持分页、搜索、筛选、排序） |
| `POST` | `/api/todos` | 创建待办事项（支持附带标签） |
| `GET` | `/api/todos/<id>` | 获取单个待办（含关联标签） |
| `PUT` | `/api/todos/<id>` | 更新待办事项 |
| `DELETE` | `/api/todos/<id>` | 删除待办事项（级联解除关联） |
| `POST` | `/api/todos/<id>/toggle` | 切换完成状态 |
| `POST` | `/api/todos/batch/delete-completed` | 批量删除已完成 |
| `POST` | `/api/todos/<id>/tags` | 为待办添加标签 |
| `PUT` | `/api/todos/<id>/tags` | 覆盖设置待办标签 |
| `DELETE` | `/api/todos/<id>/tags/<tag_id>` | 移除待办的某个标签 |

### 标签 (Tags)

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/tags` | 获取标签列表（含待办计数，批量聚合） |
| `POST` | `/api/tags` | 创建标签 |
| `GET` | `/api/tags/<id>` | 获取标签详情（含关联待办列表） |
| `PUT` | `/api/tags/<id>` | 更新标签名称或颜色 |
| `DELETE` | `/api/tags/<id>` | 删除标签（自动解除关联） |

### 统计与监控

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/stats` | 聚合统计（热点、分类、优先级、完成状态） |
| `GET` | `/api/stats/dashboard` | 仪表盘（日趋势、优先级分布、分类统计、Top 标签） |
| `GET` | `/health` | 增强健康检查（DB / Redis / 磁盘 / 内存） |
| `GET` | `/metrics` | Prometheus 兼容指标 |

### 查询参数

```
GET /api/todos?page=1&per_page=20&search=关键词&priority=high&category=work&sort_by=created_at&sort_order=desc
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `page` | int | 页码（默认 1） |
| `per_page` | int | 每页条数（1-100，默认 20） |
| `search` | str | 按标题/描述模糊搜索 |
| `completed` | str | 筛选：`true`/`false` |
| `priority` | str | 筛选：`low`/`medium`/`high` |
| `category` | str | 筛选：`personal`/`work`/`study`/`health`/`other` |
| `due_before` | str | 筛选截止日期之前的任务 |
| `sort_by` | str | 排序字段：`created_at`/`updated_at`/`due_date`/`priority`/`title` |
| `sort_order` | str | 排序方向：`asc`/`desc`（默认 `desc`） |

---

## 测试

```bash
# 运行全部测试
make test

# 覆盖率报告（HTML + XML）
make coverage

# 测试特定模块
pytest tests/ -v -k "TestTagCRUD"

# 带覆盖率 + XML 输出
make test-all

# 覆盖率门槛：最低 80%（pytest.ini / pyproject.toml 配置）
```

**测试统计：**

| 类别 | 测试数 | 覆盖内容 |
|------|--------|----------|
| 待办 CRUD | 45 | 创建、查询、更新、删除、切换、边界值 |
| 搜索分页 | 14 | 搜索、筛选、排序、分页 |
| 标签系统 | 10 | 标签 CRUD + 多对多关联 |
| 统计分析 | 3 | stats + dashboard + 标签频率 |
| 数据模型 | 6 | 序列化、默认值、关系、约束 |
| 事务安全 | 4 | 回滚、批量、savepoint |
| Mock 测试 | 10 | Redis 缓存命中/未命中/降级/失效 |
| 并发测试 | 3 | 批量创建、反复切换、标签一致性 |
| 监控指标 | 7 | /health 增强检查、/metrics Prometheus 指标 |
| 部署配置 | 4 | 工厂模式、日志、错误处理 |
| 其他 | 5 | 集成测试、边界值、HTTP 状态码 |
| Schema 与校验 | 20 | Schema 输入/输出、校验器边界与异常路径 |
| Repository 层 | 12 | 数据访问、事务控制、聚合查询 |
| 缓存与日志 | 15 | 降级分支、热点统计、production 分支 |
| 异常与错误 | 18 | 自定义异常、全局错误处理器 |
| API 边界 | 17 | 无效参数、空请求体、不存在资源 |
| **总计** | **193** | **覆盖率 91%** |

---

## 架构设计

### 分层架构

```
┌─────────────────────────────────────────┐
│              Nginx (反向代理)              │
│        速率限制 / 安全头 / Gzip            │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│           Gunicorn (多 Worker)            │
│          WSGI Server + 进程管理            │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│            Flask Application              │
│  ┌──────────────────────────────────┐   │
│  │     API 层 (Blueprint 路由)        │   │
│  │  todos / tags / stats / health    │   │
│  ├──────────────────────────────────┤   │
│  │     Schema 层 (输入/输出 DTO)       │   │
│  │  TodoCreate / TodoUpdate / ...    │   │
│  ├──────────────────────────────────┤   │
│  │     Service 层 (业务逻辑)          │   │
│  │  todo_service / tag_service       │   │
│  ├──────────────────────────────────┤   │
│  │     Repository 层 (数据访问)       │   │
│  │  TodoRepository / TagRepository   │   │
│  ├──────────────────────────────────┤   │
│  │     Model 层 (ORM 数据模型)        │   │
│  │  Todo / Tag / todo_tags           │   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │   Utils (校验 / 缓存 / 日志)       │   │
│  │   Errors (全局错误处理器)          │   │
│  │   Exceptions (自定义异常层次)      │   │
│  └──────────────────────────────────┘   │
└────────┬──────────────┬──────────────────┘
         │              │
  ┌──────▼──────┐ ┌─────▼──────┐
  │ PostgreSQL  │ │   Redis    │
  │  持久化存储  │ │   缓存层    │
  └─────────────┘ └────────────┘
```

### 数据模型

```
┌─────────────┐       ┌──────────────────┐       ┌─────────────┐
│    Todo     │       │   todo_tags      │       │     Tag     │
├─────────────┤       ├──────────────────┤       ├─────────────┤
│ id (PK)     │──1:N──│ todo_id (FK)     │──N:1──│ id (PK)     │
│ title       │       │ tag_id (FK)      │       │ name (UNIQUE)│
│ description │       │ assigned_at      │       │ color       │
│ priority    │       └──────────────────┘       │ created_at  │
│ category    │                                  └─────────────┘
│ due_date    │
│ completed   │
│ created_at  │
│ updated_at  │
└─────────────┘

索引：
  todos: title, completed, priority, due_date, created_at,
         (completed, priority), (category, priority)
  tags: name (UNIQUE)
  todo_tags: todo_id, tag_id (复合 PK)
```

### 缓存策略

采用 **Cache-Aside（旁路缓存）** 模式：

```
读取流程：Client → API → Redis 缓存？
                        ├── 命中 → 返回缓存
                        └── 未命中 → DB 查询 → 回写缓存 → 返回

写入流程：Client → API → DB 写入 → 失效相关缓存 → 返回
```

- **缓存粒度**：待办列表（`todos:list`）
- **TTL**：默认 30 秒（可通过 `CACHE_TTL` 环境变量调整）
- **降级策略**：Redis 不可用时自动跳过缓存，直接读写数据库，零影响
- **统计**：使用 Redis SCAN 获取今日 API 访问热点

### 配置管理

遵循 [12-Factor App](https://12factor.net/zh_cn/) 原则：

```
config.py
├── BaseConfig          ← 共享配置 + 环境变量
│   ├── DevelopmentConfig   ← DEBUG=True, SQLite
│   ├── TestingConfig       ← TESTING=True, 内存 SQLite
│   └── ProductionConfig    ← DEBUG=False, PostgreSQL + 连接池
```

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

- 当数据库不可用时，HTTP 状态码返回 **503**，`status` 为 `"degraded"`
- 当磁盘使用率 >90% 或内存 >95% 时，同样返回 degraded 状态（阈值可通过 `HEALTH_DISK_THRESHOLD` / `HEALTH_MEM_THRESHOLD` 环境变量配置）
- Redis 不可用**不会**触发降级，因为应用有优雅降级机制

### Prometheus 指标

```bash
curl http://localhost:5000/metrics
```

关键指标：

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `todo_total` | Gauge | 待办事项总数 |
| `todo_completed` | Gauge | 已完成数 |
| `todo_pending` | Gauge | 未完成数 |
| `todo_by_priority` | Gauge | 按优先级分布（low/medium/high） |
| `todo_tags_total` | Gauge | 标签总数 |
| `process_memory_usage_bytes` | Gauge | 内存使用量 |
| `process_cpu_percent` | Gauge | CPU 使用率 |
| `redis_available` | Gauge | Redis 可用性（1/0） |

---

## 安全特性

| 特性 | 实现 |
|------|------|
| 速率限制 | Nginx `limit_req`（API 10r/s，页面 20r/s） |
| 安全头 | X-Frame-Options、X-XSS-Protection、CSP、Referrer-Policy、Permissions-Policy |
| 输入校验 | 服务端多层校验（Validator → API → Service），支持自定义异常（ValidationException） |
| SQL 注入防护 | SQLAlchemy ORM 参数化查询 + LIKE 转义 + Repository 层统一参数化 |
| CORS 配置 | Flask-CORS 白名单控制 |
| 非 root 运行 | Docker 容器使用非特权 `app` 用户 |
| 密钥检查 | 部署脚本自动检查生产环境 SECRET_KEY 安全性 |
| HSTS | SSL 模板中预置（需配置证书后启用） |
| 指标保护 | `/metrics` 端点通过 Nginx IP 白名单限制 |

---

## 实训学习要点

本实训项目涵盖以下核心技能：

1. **Web 开发基础**
   - Flask 应用工厂模式与模块化分层架构
   - RESTful API 设计
   - Jinja2 模板渲染
   - Flask 扩展生态（SQLAlchemy / Migrate / CORS）
   - Blueprint 路由组织

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
   - 自动化部署脚本（含安全检查）

5. **监控与运维**
   - 结构化 JSON 日志
   - 健康检查端点（DB / Redis / 磁盘 / 内存）
   - Prometheus 指标暴露
   - 数据库备份与恢复

6. **软件工程实践**
   - 关注点分离（API → Service → Model 分层）
   - 统一错误处理
   - 输入校验集中管理
   - 缓存策略设计（Cache-Aside + 降级）
   - 环境配置管理（12-Factor App）

---

## 许可证

本项目采用 [MIT License](LICENSE)，允许自由使用、修改和分发。

本项目为 **AiCoding 实训教学项目**，仅供学习参考。
