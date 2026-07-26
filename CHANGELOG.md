# 更新日志 (Changelog)

本文档记录 AiCoding Todo 项目的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [1.4.0] - 2026-07-26

### 新增

- **Repository 层** (`app/repositories/`)：封装所有 ORM 操作，Service 层通过 Repository 访问数据
  - `TodoRepository`：Todo CRUD + 分页 + 聚合查询（20+ 方法）
  - `TagRepository`：Tag CRUD + 批量查询 + 使用量聚合
- **Schema/DTO 层** (`app/schemas/`)：使用 dataclass 定义输入/输出结构，与 ORM 模型解耦
  - `TodoCreateSchema` / `TodoUpdateSchema` / `TodoOutSchema`
  - `TagCreateSchema` / `TagUpdateSchema` / `TagOutSchema`
- **自定义异常层次** (`app/exceptions.py`)：`AppException` → `NotFoundException` / `ConflictException` / `ValidationException` / `BusinessException`
- **CI/CD 配置** (`.github/workflows/ci.yml`)：多 Python 版本矩阵测试 + Docker 构建验证
- **`pyproject.toml`**：现代 Python 项目配置（含 pytest / mypy / flake8 配置）

### 变更

- 所有 `__init__.py` 增加显式导出控制（`__all__`）
- Service 层统一使用 Repository 访问数据库，不再直接操作 `Model.query`
- API 层异常处理改用自定义异常（`ValidationException` / `ConflictException` / `NotFoundException`）
- 错误处理器注册 `AppException` 全局兜底
- `tests/conftest.py` 移除 `sys.path.insert` hack
- `pytest.ini` 配置迁移到 `pyproject.toml`

### 修复

- 移除 `_HAS_PSUTIL` 未使用变量（`todo_service.py`）
- 移除未使用的 `savepoint` 赋值（`todo_service.py`）
- 修正 `metrics_text` 版本号 `1.0.0` → `1.4.0`
- 移除 `test_mock.py` 多余的 `sys.path.insert` hack
- Schema 输入类添加 `TODO: v1.5` 注释标记未使用状态

### 测试

- 新增 `test_coverage_supplement.py`（82 用例）
- 测试用例总数：111 → **193**
- 覆盖率：84.95% → **91.10%**
- 覆盖新增模块：Schema（100%）、Repository（84%）、Exceptions（100%）、校验器（100%）、缓存（100%）、日志（100%）、错误处理器（89%）

---

## [1.3.0] - 2026-07-26

### 新增

- 完整 API 接口文档（`API.md`）：20 个端点，含请求/响应示例、数据模型、字段约束
- 部署运维指南（`DEPLOYMENT.md`）：Docker 架构、Nginx 配置、备份恢复、性能调优、故障排查
- 开发指南（`DEVELOPMENT.md`）：项目结构、编码规范、测试指南、数据库迁移、调试技巧
- `README.md` 新增文档导航索引

### 变更

- 优先级排序从字母序改为权重排序（high → medium → low），语义更合理
- 健康检查磁盘/内存阈值改为可配置（`HEALTH_DISK_THRESHOLD` / `HEALTH_MEM_THRESHOLD`），默认值提高至 90%/95%
- `priority` 和 `category` 筛选参数传入无效值时返回 400（与 `completed` 行为统一）

### 修复

- 修复 `tests/conftest.py` 中 `create_todo` 辅助函数的 toggle 逻辑缺陷

---

## [1.2.0] - 2026-07-26

### 新增

- 项目结构大厂化重构：从单体 `app.py` 拆分为模块化分层架构
  - `app/` 应用包（API → Service → Model → Utils → Errors 五层分离）
  - API 层按领域拆分为 4 个 Blueprint：`health`、`todos`、`tags`、`stats`
  - Service 层封装所有业务逻辑（`todo_service` / `tag_service`）
  - Model 层独立文件（`todo.py` / `tag.py`）
  - Utils 层集中管理校验、缓存、日志
  - Errors 层统一全局错误处理器
- 配置类继承体系（`BaseConfig → Dev/Test/Prod`）
- 扩展延迟绑定模式（`extensions.py`）
- 统一输入校验器（`validators.py`），API 和 Service 层复用
- 向后兼容的 `app.py` 入口（Gunicorn 命令无需修改）

### 变更

- 测试覆盖率从 84.6% 提升至 **85.22%**
- `README.md` 全面更新：补充分层架构说明、API 表格增加关联操作端点、补充查询参数表、补充 Prometheus 指标表
- 测试文件适配新模块导入路径

### 修复

- 修复 `SQLALCHEMY_ENGINE_OPTIONS` 配置对 SQLite 不兼容的问题（仅在生产环境启用连接池）

---

## [1.1.0] - 2026-07-25

### 新增

- 标签系统（Tag CRUD + Todo↔Tag 多对多关联）
- 标签关联操作 API：
  - `POST /api/todos/<id>/tags` — 添加标签
  - `PUT /api/todos/<id>/tags` — 覆盖设置标签
  - `DELETE /api/todos/<id>/tags/<tag_id>` — 移除标签
- 标签统计：按使用频率排序的 Top 标签、标签关联计数
- 批量删除已完成待办（`POST /api/todos/batch/delete-completed`）
- 仪表盘多维统计（`GET /api/stats/dashboard`）：
  - 7 天日趋势
  - 优先级分布 + 完成率
  - 分类统计 + 逾期数
  - Top 10 标签

### 变更

- 测试用例从 75 个增至 **111 个**
- 测试覆盖：标签 CRUD、关联操作、并发标签一致性、批量删除
- `init.sql` 更新：新增 `tags` 和 `todo_tags` 表结构
- Alembic 迁移新增 `002_add_tags.py`

---

## [1.0.0] - 2026-07-24

### 新增

- 待办事项核心 CRUD（创建、查询列表、查询详情、更新、删除）
- 待办完成状态切换
- 搜索、筛选（按完成状态/优先级/分类/截止日期）、排序、分页
- 聚合统计（按分类+优先级分组、完成状态统计、逾期统计）
- 增强健康检查端点（数据库、Redis、磁盘、内存）
- Prometheus 兼容指标端点（`/metrics`）
- Redis Cache-Aside 缓存（待办列表缓存 + 优雅降级）
- API 调用热度统计（Redis SCAN）
- 前端单页应用（Bootstrap 5 + 原生 JS TodoApp 类）
  - 表单前端校验（标题非空、长度、截止时间合法性）
  - 实时字符计数
  - Toast 通知
  - XSS 防护
  - 完成状态/优先级筛选 + 排序
- 数据库设计：`todos` 表 + 7 个复合索引
- Alembic 迁移管理（`001_initial_schema.py`）
- Docker 多阶段构建 + 四服务编排（app + PostgreSQL + Redis + Nginx）
- Nginx 反向代理配置：
  - 速率限制（API 10r/s，页面 20r/s）
  - 安全头（CSP、X-Frame-Options、X-XSS-Protection 等）
  - SSL/TLS 配置模板（含 HSTS）
  - `/metrics` IP 白名单保护
  - Gzip 压缩
- Gunicorn 生产配置（多 worker + 多线程 + 连接限制 + 优雅重启）
- 自动化部署脚本（含安全检查：密钥强度、FLASK_ENV 验证）
- 容器启动脚本（等待依赖 → 迁移 → 启动）
- Makefile 快捷命令集（开发/测试/构建/部署/运维/备份/恢复）
- 75 个 pytest 测试用例 + 84.6% 覆盖率
- Mock 测试（Redis 缓存命中/未命中/失效/降级、日志验证、并发安全）
- 结构化 JSON 日志 + 按日轮转（30 天保留）
- 运维脚本：健康检查（Nagios 兼容）、数据库备份（压缩 + 清理）
- 完整项目文档（`README.md`）
- SQL 练习文件（`sql_practice.sql`）：基础查询、聚合、关联、CTE、事务、窗口函数

---

## 版本说明

| 版本 | 日期 | 测试用例 | 覆盖率 | 主要变更 |
|------|------|----------|--------|----------|
| 1.4.0 | 2026-07-26 | 193 | 91.10% | 架构升级：Repository + Schema + 自定义异常 + CI/CD + pyproject.toml + 测试补充 |
| 1.3.0 | 2026-07-26 | 111 | 85.02% | 完善文档体系 + 优先级排序/健康检查/筛选行为优化 |
| 1.2.0 | 2026-07-26 | 111 | 85.22% | 模块化架构重构（分层架构） |
| 1.1.0 | 2026-07-25 | 111 | 84.60% | 标签系统 + 仪表盘 |
| 1.0.0 | 2026-07-24 | 75 | 84.60% | 初始版本（核心功能） |
