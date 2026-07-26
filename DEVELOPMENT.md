# 开发指南

> 适用于 AiCoding Todo 本地开发与贡献

---

## 目录

- [环境准备](#环境准备)
- [项目结构](#项目结构)
- [快速启动](#快速启动)
- [架构设计](#架构设计)
- [开发规范](#开发规范)
- [测试指南](#测试指南)
- [数据库迁移](#数据库迁移)
- [调试技巧](#调试技巧)
- [常见问题](#常见问题)

---

## 环境准备

### 必需

- Python 3.9+
- pip（最新版）
- Git

### 推荐

- Docker & Docker Compose（用于完整环境测试）
- SQLite（开发数据库，无需额外安装）

### 安装依赖

```bash
git clone <repo-url>
cd AiCoding_Todo
pip install -r requirements.txt
```

---

## 项目结构

```
AiCoding_Todo/
├── app/                          # 应用核心包
│   ├── __init__.py               # create_app() 应用工厂 + 蓝图注册
│   ├── config.py                 # 配置类继承体系
│   ├── extensions.py             # 扩展延迟绑定
│   ├── exceptions.py             # 自定义异常层次
│   ├── api/                      # API 路由层
│   │   ├── health.py             # 首页 / 健康检查 / Prometheus
│   │   ├── todos.py              # Todo CRUD + 标签关联
│   │   ├── tags.py               # Tag CRUD
│   │   └── stats.py              # 统计 / 仪表盘
│   ├── services/                 # 业务逻辑层
│   │   ├── todo_service.py       # Todo 业务逻辑
│   │   └── tag_service.py        # Tag 业务逻辑
│   ├── repositories/             # 数据访问层（Repository 模式）
│   │   └── __init__.py           # TodoRepository + TagRepository
│   ├── schemas/                  # Schema/DTO 层（dataclass）
│   │   ├── __init__.py           # 6 个 Schema 集中导出
│   │   ├── todo.py               # Todo 输入/输出 Schema
│   │   └── tag.py                # Tag 输入/输出 Schema
│   ├── models/                   # 数据模型层
│   │   ├── todo.py               # Todo ORM
│   │   └── tag.py                # Tag ORM + 关联表
│   ├── utils/                    # 工具层
│   │   ├── validators.py         # 输入校验
│   │   ├── cache.py              # Redis 缓存辅助
│   │   └── logging.py            # 日志配置
│   └── errors/                   # 错误处理
│       └── handlers.py           # 全局错误处理器（含 AppException）
│
├── tests/                        # 测试套件（193 用例）
│   ├── conftest.py               # 集中式 Fixture
│   ├── test_app.py               # 核心功能测试
│   ├── test_mock.py              # Mock 与并发测试
│   └── test_coverage_supplement.py  # 覆盖率补充测试
│
├── migrations/                   # Alembic 数据库迁移
│   └── versions/                 # 迁移版本文件
│
├── templates/
│   └── index.html                # 前端单页应用
│
├── scripts/                      # 运维脚本
│   ├── healthcheck.sh            # 健康检查
│   └── backup.sh                 # 数据库备份
│
├── app.py                        # 开发入口（向后兼容）
├── gunicorn.conf.py              # Gunicorn 配置
├── requirements.txt              # Python 依赖
├── Dockerfile                    # Docker 构建
├── docker-compose.yml            # 服务编排
├── nginx.conf                    # Nginx 配置
├── Makefile                      # 快捷命令
├── env.example                   # 环境变量模板
├── pytest.ini                    # 测试配置
│
├── README.md                     # 项目说明
├── API.md                        # API 接口文档
├── CHANGELOG.md                  # 更新日志
├── DEPLOYMENT.md                 # 部署运维指南
└── DEVELOPMENT.md                # 本文档
```

---

## 快速启动

### 开发模式

```bash
# 1. 配置环境
cp env.example .env
# 开发模式默认使用 SQLite，无需额外配置

# 2. 初始化数据库
flask db upgrade

# 3. 启动开发服务器
python app.py
# 访问 http://localhost:5000
```

### 使用 Makefile

```bash
make install    # 安装依赖
make run        # 启动开发服务器
make test       # 运行测试
make coverage   # 覆盖率报告
make lint       # 代码检查
make clean      # 清理临时文件
```

### 使用脚本

```bash
# 运行测试
./run_tests.sh                     # 基本测试
./run_tests.sh --coverage          # 含覆盖率
./run_tests.sh -k TestCreateTodo   # 运行特定测试类
./run_tests.sh --verbose           # 详细输出
```

---

## 架构设计

### 分层架构

```
┌─────────────────────────────────┐
│         API 层 (Blueprint)       │  ← HTTP 请求/响应
│  校验输入 → 调用 Service → 返回  │
├─────────────────────────────────┤
│       Schema 层 (DTO)            │  ← 输入/输出结构定义
│  dataclass: Create/Update/Out    │
├─────────────────────────────────┤
│       Service 层 (业务逻辑)       │  ← 纯 Python，无 HTTP 依赖
│  参数验证 → 调用 Repository → 返回│
├─────────────────────────────────┤
│      Repository 层 (数据访问)     │  ← 封装所有 ORM 操作
│  纯静态方法，不持有状态           │
├─────────────────────────────────┤
│        Model 层 (ORM)            │  ← 数据模型定义
│  Todo / Tag / todo_tags          │
├─────────────────────────────────┤
│        数据存储层                 │
│  PostgreSQL / SQLite / Redis      │
└─────────────────────────────────┘
```

**核心原则**：
- **API 层**：只做 HTTP ↔ 业务逻辑的转换，不直接操作数据库
- **Schema 层**：定义 API 输入/输出的数据结构，与 ORM 模型解耦
- **Service 层**：封装所有业务逻辑，可被 API 层和 CLI 复用
- **Repository 层**：封装所有 ORM 操作（纯静态方法），Service 层通过 Repository 访问数据
- **Model 层**：仅定义数据结构和序列化方法
- **单向依赖**：API → Schema → Service → Repository → Model，不可反向

### 配置管理

```
BaseConfig          ← 共享配置 + 环境变量
├── DevelopmentConfig   ← DEBUG=True, SQLite
├── TestingConfig       ← TESTING=True, 内存 SQLite
└── ProductionConfig    ← DEBUG=False, PostgreSQL + 连接池
```

通过 `create_app(config_name)` 工厂函数选择配置。

### 缓存策略

采用 **Cache-Aside** 模式：

```
读取: Client → API → Redis? → 命中: 返回缓存
                           → 未命中: DB → 回写缓存 → 返回
写入: Client → API → DB 写入 → 失效缓存 → 返回
```

Redis 不可用时自动降级，直接读写数据库，零影响。

---

## 开发规范

### 添加新 API 端点

1. **Schema 层**：在 `app/schemas/` 中定义输入/输出 dataclass
2. **Repository 层**：在 `app/repositories/` 中实现数据访问方法
3. **Service 层**：在 `app/services/` 中实现业务逻辑，调用 Repository
4. **API 层**：在 `app/api/` 中添加路由，调用 Service
5. **校验**：复用 `app/utils/validators.py` 或使用自定义异常（`ValidationException`）
6. **测试**：在 `tests/` 中添加测试

### 示例：添加"按标签筛选待办"功能

```python
# 1. app/repositories/__init__.py（TodoRepository 中）
@staticmethod
def find_all(filters: dict, tag_id: Optional[int] = None, ...):
    query = Todo.query
    if tag_id is not None:
        query = query.join(Todo.tags).filter(Tag.id == tag_id)

# 2. app/services/todo_service.py
def list_todos(tag_id: Optional[int] = None, ...):
    todos, pagination = TodoRepository.find_all(tag_id=tag_id, ...)

# 3. app/api/todos.py
@todos_bp.route("", methods=["GET"])
def get_todos():
    tag_id = request.args.get("tag_id", type=int)
    result, pagination = todo_service.list_todos(tag_id=tag_id, ...)

# 4. tests/test_app.py
def test_filter_by_tag(self, client):
    ...
```

### 编码风格

- 遵循 **PEP 8**
- 类型注解：所有函数参数和返回值添加类型注解
- Docstring：所有公开函数使用 Google 风格 docstring
- 命名：`snake_case` 变量/函数，`PascalCase` 类，`UPPER_CASE` 常量

### 输入校验

所有输入校验集中到 `app/utils/validators.py`：

```python
from app.utils.validators import validate_todo_data, validate_tag_name, validate_color

# 校验 Todo 数据
is_valid, error = validate_todo_data(data, is_create=True)

# 校验标签名
is_valid, error = validate_tag_name(name, max_length=50)

# 校验颜色
is_valid, error = validate_color(color)
```

### 错误处理

项目使用自定义异常层次（`app/exceptions.py`）：

```python
from app.exceptions import (
    AppException,        # 基类（500）
    NotFoundException,   # 404
    ConflictException,   # 409
    ValidationException, # 400
    BusinessException,   # 422
)

# Service 层使用自定义异常
from app.exceptions import NotFoundException, ConflictException

if not todo:
    raise NotFoundException("待办事项不存在")
if existing_tag:
    raise ConflictException("标签名称已存在")

# API 层无需 try/except，由全局错误处理器统一处理
# 全局错误处理器（app/errors/handlers.py）处理：
# - AppException 及其子类（自动映射到对应 HTTP 状态码）
# - 400 Bad Request（JSON 解析失败）
# - 404 Not Found
# - 405 Method Not Allowed
# - 500 Internal Server Error（兜底）
```

---

## 测试指南

### 测试结构

| 文件 | 内容 | 用例数 |
|------|------|--------|
| `test_app.py` | 核心功能：CRUD / 搜索 / 标签 / 统计 / 监控 | 93 |
| `test_mock.py` | Mock 测试：缓存 / 日志 / 并发 | 18 |
| `test_coverage_supplement.py` | 覆盖率补充：Schema / Repository / 校验器 / 异常 / 边界值 | 82 |

### 运行测试

```bash
# 全部测试（193 用例，覆盖率 ≥ 80%）
pytest tests/ -v

# 覆盖率（HTML + XML）
pytest tests/ -v --cov=app --cov-report=html --cov-report=xml

# 特定测试类
pytest tests/ -v -k "TestCreateTodo"

# 特定测试方法
pytest tests/ -v -k "test_create_basic"

# 覆盖率补充测试
pytest tests/test_coverage_supplement.py -v
```

### 测试 Fixture

`tests/conftest.py` 提供：

| Fixture | 用途 |
|---------|------|
| `app` | 独立 SQLite 测试应用 |
| `client` | Flask 测试客户端 |
| `app_context` | 应用上下文（直接操作 DB） |
| `sample_todo_data` | 示例待办字典 |
| `populated_db` | 预填充 10 条数据 |
| `populated_with_tags` | 预填充带标签数据 |
| `mock_redis` | Mock Redis（缓存未命中） |
| `mock_redis_with_cache` | Mock Redis（缓存命中） |
| `create_todo()` | 辅助创建函数 |
| `create_tag()` | 辅助创建标签函数 |

### 编写新测试

```python
class TestNewFeature:

    def test_basic_behavior(self, client):
        # 创建测试数据
        data, status = create_todo(client, "测试", priority="high")
        assert status == 201

        # 测试新端点
        resp = client.get("/api/new-endpoint")
        assert resp.status_code == 200

    def test_edge_case(self, client):
        resp = client.post("/api/new-endpoint",
                          data=json.dumps({"invalid": True}),
                          content_type="application/json")
        assert resp.status_code == 400
```

---

## 数据库迁移

### 创建新迁移

```bash
# 修改模型后，生成迁移文件
flask db migrate -m "描述你的变更"

# 检查生成的迁移文件
cat migrations/versions/003_xxx.py

# 应用迁移
flask db upgrade
```

### 迁移管理

```bash
flask db upgrade          # 升级到最新
flask db downgrade        # 回滚一步
flask db history          # 查看迁移历史
flask db current          # 查看当前版本
flask db stamp head       # 标记为最新（不执行迁移）
```

### 迁移文件规范

```python
"""描述你的变更

Revision ID: xxx
Revises: yyy
Create Date: 2026-07-26 10:30:00.000000
"""
```

### 注意事项

- 迁移文件生成后应**人工检查**，确保自动检测的变更正确
- `init.sql` 仅用于 Docker 首次初始化，正式迁移以 Alembic 为准
- 修改 `init.sql` 时需同步更新 Alembic 迁移

---

## 调试技巧

### Flask 调试模式

```bash
# 开发模式自动启用 DEBUG=True
FLASK_ENV=development python app.py
```

启用后：
- 自动重载代码变更
- 详细错误页面
- 交互式调试器

### 日志调试

```python
import logging
logger = logging.getLogger(__name__)
logger.debug(f"变量值: {value}")
logger.info("执行到某步骤")
logger.exception("异常详情")  # 自动附带 traceback
```

设置日志级别：
```bash
LOG_LEVEL=DEBUG python app.py
```

### 数据库查询调试

```python
# 查看 SQL 语句
from app.extensions import db
db.session.execute(text("EXPLAIN ANALYZE SELECT ..."))
```

### VS Code 调试配置

`.vscode/launch.json`：
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Flask App",
      "type": "python",
      "request": "launch",
      "module": "flask",
      "env": {"FLASK_APP": "app:create_app", "FLASK_ENV": "development"},
      "args": ["run", "--host=0.0.0.0", "--port=5000"],
      "jinja": true
    }
  ]
}
```

---

## 常见问题

### Q: 开发时如何切换数据库？

开发默认使用 SQLite。如需使用 PostgreSQL：

```bash
# .env 中设置
DATABASE_URL=postgresql://todo_user:todo_password@localhost:5432/todo_db
```

### Q: 测试运行很慢怎么办？

```bash
# 使用内存数据库（默认）
# 运行特定测试
pytest tests/ -k "TestCreateTodo"

# 并行运行（需要 pytest-xdist）
pip install pytest-xdist
pytest tests/ -n auto
```

### Q: Redis 连接失败影响开发吗？

不影响。应用会自动降级，直接读写数据库。开发时可以完全不用 Redis。

### Q: 如何添加新的优先级/分类？

1. 修改 `app/config.py` 中的 `VALID_PRIORITIES` / `VALID_CATEGORIES`
2. 修改 `app/utils/validators.py` 中的校验逻辑
3. 更新数据库约束（新建迁移）
4. 更新测试用例
5. 更新文档

### Q: 如何添加新的排序字段？

1. 在 `todo_service.py` 的 `sort_columns` 字典中添加映射
2. 如果是非普通列排序（如 priority 权重），在 `list_todos` 中添加特殊处理分支
3. 添加测试用例
