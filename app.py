import logging
import os
import time
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

import redis as redis_lib
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from dotenv import load_dotenv
from pythonjsonlogger import jsonlogger
from sqlalchemy import Index, and_, or_, func, text, event
from sqlalchemy.engine import Engine

# ──────────────────────────────────────────────
# 扩展实例（延迟绑定到 app）
# ──────────────────────────────────────────────
db = SQLAlchemy()
migrate = Migrate()
redis_client = None  # 延迟初始化

# ──────────────────────────────────────────────
# SQLite 外键支持
# ──────────────────────────────────────────────

@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """为 SQLite 启用外键约束（测试环境必要）。"""
    import sqlite3
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# ──────────────────────────────────────────────
# 常量定义
# ──────────────────────────────────────────────
VALID_PRIORITIES = {"low", "medium", "high"}
VALID_CATEGORIES = {"personal", "work", "study", "health", "other"}
TITLE_MIN_LENGTH = 1
TITLE_MAX_LENGTH = 200

# ──────────────────────────────────────────────
# 日志配置（按天轮转 + JSON 格式化）
# ──────────────────────────────────────────────

def setup_logging(app):
    """配置应用日志：按天轮转，支持 JSON 和生产/开发级别切换。"""
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # 确保日志目录存在
    log_dir = os.getenv("LOG_DIR", "/app/logs")
    os.makedirs(log_dir, exist_ok=True)

    # 根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除已有 handler（避免重复）
    root_logger.handlers.clear()

    flask_env = os.getenv("FLASK_ENV", "production")

    if flask_env == "development":
        # 开发环境：控制台输出，人类可读格式
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_fmt)
        root_logger.addHandler(console_handler)
    else:
        # 生产环境：控制台 + JSON 文件日志，按天轮转
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(message)s")
        console_handler.setFormatter(console_fmt)
        root_logger.addHandler(console_handler)

        # JSON 格式文件日志，每天午夜轮转，保留 30 天
        file_handler = TimedRotatingFileHandler(
            filename=os.path.join(log_dir, "app.log"),
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        json_fmt = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        file_handler.setFormatter(json_fmt)
        root_logger.addHandler(file_handler)

    app.logger.info(f"日志系统初始化完成 (level={log_level_name}, env={flask_env})")


# ──────────────────────────────────────────────
# Redis 缓存辅助
# ──────────────────────────────────────────────

def get_redis():
    """获取 Redis 客户端（懒初始化）。"""
    global redis_client
    if redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            redis_client = redis_lib.from_url(redis_url, socket_connect_timeout=2, decode_responses=True)
            redis_client.ping()
            logging.getLogger(__name__).info("Redis 连接成功")
        except Exception as e:
            logging.getLogger(__name__).warning(f"Redis 不可用，缓存功能将禁用: {e}")
            redis_client = False
    return redis_client if redis_client is not False else None


def increment_visit_stat(endpoint):
    """记录 API 调用热度统计。"""
    r = get_redis()
    if r:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"stats:{endpoint}:{today}"
        r.incr(key)
        r.expire(key, 86400 * 7)


def get_hot_stats():
    """获取今日访问统计。"""
    r = get_redis()
    if not r:
        return {}
    today = datetime.utcnow().strftime("%Y-%m-%d")
    keys = r.keys(f"stats:*:{today}")
    stats = {}
    for key in keys:
        endpoint = key.decode() if isinstance(key, bytes) else key
        endpoint = endpoint.replace(f"stats:", "").replace(f":{today}", "")
        stats[endpoint] = int(r.get(key) or 0)
    return stats


def cache_get(key):
    """从 Redis 读取缓存。"""
    r = get_redis()
    if not r:
        return None
    import json
    val = r.get(key)
    return json.loads(val) if val else None


def cache_set(key, value, ttl=60):
    """写入 Redis 缓存。"""
    r = get_redis()
    if not r:
        return
    import json
    r.setex(key, ttl, json.dumps(value, ensure_ascii=False))


# ──────────────────────────────────────────────
# 多对多关联表：待办事项 ↔ 标签
# ──────────────────────────────────────────────
todo_tags = db.Table(
    "todo_tags",
    db.Column("todo_id", db.Integer, db.ForeignKey("todos.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    db.Column("assigned_at", db.DateTime, default=datetime.utcnow),
    # 复合索引加速反向查询（查找使用某标签的所有待办）
    Index("ix_todo_tags_todo_id", "todo_id"),
    Index("ix_todo_tags_tag_id", "tag_id"),
)


# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

class Todo(db.Model):
    """待办事项模型。

    字段：
        id, title, description, completed, priority,
        category, due_date, created_at, updated_at

    关联：
        tags (M:N → Tag)
    """

    __tablename__ = "todos"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(TITLE_MAX_LENGTH), nullable=False)
    description = db.Column(db.Text, default="")
    completed = db.Column(db.Boolean, default=False)
    priority = db.Column(db.String(20), default="medium")
    category = db.Column(db.String(20), default="other")
    due_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── 多对多：Todo ↔ Tag ──
    tags = db.relationship(
        "Tag",
        secondary=todo_tags,
        lazy="joined",
        backref=db.backref("todos", lazy="dynamic"),
    )

    # ── 表级索引（统一管理，避免与列级 index=True 冲突） ──
    __table_args__ = (
        Index("ix_todos_title", "title"),
        Index("ix_todos_completed", "completed"),
        Index("ix_todos_priority", "priority"),
        # 复合索引：按完成状态 + 优先级（高频筛选组合）
        Index("ix_todos_completed_priority", "completed", "priority"),
        # 复合索引：按分类 + 优先级
        Index("ix_todos_category_priority", "category", "priority"),
        # 截止日期索引（排序和筛选）
        Index("ix_todos_due_date", "due_date"),
        # 创建时间索引（默认排序）
        Index("ix_todos_created_at", "created_at"),
    )

    def to_dict(self, include_tags=True):
        result = {
            "id": self.id,
            "title": self.title,
            "description": self.description or "",
            "completed": self.completed,
            "priority": self.priority,
            "category": self.category,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_tags:
            result["tags"] = [tag.to_dict() for tag in self.tags]
        return result


class Tag(db.Model):
    """标签模型。

    与 Todo 为多对多关系。
    字段：
        id, name, color, created_at
    """

    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    color = db.Column(db.String(7), default="#6c757d")  # 默认灰色
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_tags_name", "name"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "todo_count": len(self.todos.all()) if self.todos else 0,
        }


# ──────────────────────────────────────────────
# 请求校验辅助函数
# ──────────────────────────────────────────────

def validate_todo_data(data, is_create=False):
    """校验待办事项输入。"""
    if is_create:
        if not data or not isinstance(data, dict):
            return False, "请求体不能为空"
        if "title" not in data or not isinstance(data["title"], str) or not data["title"].strip():
            return False, "标题不能为空"

    if "title" in data:
        title = data["title"]
        if not isinstance(title, str):
            return False, "标题必须是字符串"
        stripped = title.strip()
        if len(stripped) < TITLE_MIN_LENGTH:
            return False, f"标题长度至少 {TITLE_MIN_LENGTH} 个字符"
        if len(stripped) > TITLE_MAX_LENGTH:
            return False, f"标题长度不能超过 {TITLE_MAX_LENGTH} 个字符"
        data["title"] = stripped

    if "priority" in data and data["priority"] is not None:
        if data["priority"] not in VALID_PRIORITIES:
            return False, f"优先级必须为: {', '.join(sorted(VALID_PRIORITIES))}"

    if "category" in data and data["category"] is not None:
        if data["category"] not in VALID_CATEGORIES:
            return False, f"分类必须为: {', '.join(sorted(VALID_CATEGORIES))}"

    return True, None


def parse_due_date(value):
    """解析 ISO 格式日期字符串。"""
    if value is None:
        return None, None
    if not isinstance(value, str):
        return None, "截止日期必须是 ISO 格式的字符串"
    try:
        return datetime.fromisoformat(value), None
    except (ValueError, TypeError):
        return None, "截止日期格式无效，请使用 ISO 格式（如 2025-07-26T12:00:00）"


# ──────────────────────────────────────────────
# 应用工厂
# ──────────────────────────────────────────────

def create_app(test_config=None):
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///todo.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

    if test_config:
        app.config.update(test_config)

    # 初始化日志
    setup_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)

    # ════════════════════════════════════════════
    # 页面与健康路由
    # ════════════════════════════════════════════

    @app.route("/")
    def index():
        increment_visit_stat("home")
        return render_template("index.html")

    @app.route("/health")
    def health():
        """增强健康检查：数据库、Redis、磁盘、内存。"""
        import psutil  # 可选依赖
        health_data = {"status": "ok"}

        # 数据库连通性检查
        try:
            db.session.execute(text("SELECT 1"))
            health_data["database"] = "ok"
        except Exception:
            health_data["database"] = "error"
            health_data["status"] = "degraded"

        # Redis 连通性检查
        r = get_redis()
        health_data["redis"] = "ok" if r else "unavailable"

        # 磁盘使用率（警告 > 80%）
        try:
            disk_usage = psutil.disk_usage("/")
            health_data["disk_usage_percent"] = disk_usage.percent
            if disk_usage.percent > 80:
                health_data["status"] = "degraded"
        except Exception:
            health_data["disk_usage_percent"] = "unknown"

        # 内存使用率（警告 > 90%）
        try:
            mem = psutil.virtual_memory()
            health_data["memory_usage_percent"] = mem.percent
            if mem.percent > 90:
                health_data["status"] = "degraded"
        except Exception:
            health_data["memory_usage_percent"] = "unknown"

        # 数据库记录数
        try:
            health_data["total_todos"] = Todo.query.count()
            health_data["total_tags"] = Tag.query.count()
        except Exception:
            pass

        http_status = 200 if health_data["status"] == "ok" else 503
        return jsonify(health_data), http_status

    @app.route("/metrics")
    def metrics():
        """Prometheus 兼容的指标端点（文本格式）。"""
        import platform
        import psutil

        lines = []

        # 应用信息
        lines.append("# HELP todo_app_info 待办事项应用信息")
        lines.append("# TYPE todo_app_info gauge")
        lines.append(f'todo_app_info{{version="1.0.0",python="{platform.python_version()}"}} 1')

        # 待办计数
        total = Todo.query.count()
        completed = Todo.query.filter(Todo.completed == True).count()
        pending = total - completed

        lines.append("# HELP todo_total 待办事项总数")
        lines.append("# TYPE todo_total gauge")
        lines.append(f"todo_total {total}")

        lines.append("# HELP todo_completed 已完成待办数")
        lines.append("# TYPE todo_completed gauge")
        lines.append(f"todo_completed {completed}")

        lines.append("# HELP todo_pending 未完成待办数")
        lines.append("# TYPE todo_pending gauge")
        lines.append(f"todo_pending {pending}")

        # 按优先级分布
        lines.append("# HELP todo_by_priority 按优先级分布")
        lines.append("# TYPE todo_by_priority gauge")
        for p in ("low", "medium", "high"):
            count = Todo.query.filter(Todo.priority == p).count()
            lines.append(f'todo_by_priority{{priority="{p}"}} {count}')

        # 标签计数
        tag_count = Tag.query.count()
        lines.append("# HELP todo_tags_total 标签总数")
        lines.append("# TYPE todo_tags_total gauge")
        lines.append(f"todo_tags_total {tag_count}")

        # 系统指标
        try:
            mem = psutil.virtual_memory()
            lines.append("# HELP process_memory_usage_bytes 内存使用")
            lines.append("# TYPE process_memory_usage_bytes gauge")
            lines.append(f"process_memory_usage_bytes {mem.used}")

            cpu_percent = psutil.cpu_percent(interval=0.1)
            lines.append("# HELP process_cpu_percent CPU 使用率")
            lines.append("# TYPE process_cpu_percent gauge")
            lines.append(f"process_cpu_percent {cpu_percent}")
        except Exception:
            pass

        # Redis 状态
        r = get_redis()
        lines.append("# HELP redis_available Redis 可用性 (1=可用, 0=不可用)")
        lines.append("# TYPE redis_available gauge")
        lines.append(f"redis_available {1 if r else 0}")

        return "\n".join(lines) + "\n", 200, {"Content-Type": "text/plain; charset=utf-8"}

    # ════════════════════════════════════════════
    # 统计接口（含 SQL 聚合）
    # ════════════════════════════════════════════

    @app.route("/api/stats", methods=["GET"])
    def api_stats():
        """返回统计信息：热点、聚合统计。"""
        hot = get_hot_stats()

        # ── SQL 聚合查询（展示复杂查询能力） ──
        with db.engine.connect() as conn:
            # 按分类 + 优先级统计（使用 GROUP BY + 聚合函数）
            agg_result = conn.execute(text("""
                SELECT
                    category,
                    priority,
                    COUNT(*) AS cnt
                FROM todos
                GROUP BY category, priority
                ORDER BY category, priority
            """)).fetchall()

            # 按完成状态统计
            completion_result = conn.execute(text("""
                SELECT
                    completed,
                    COUNT(*) AS cnt
                FROM todos
                GROUP BY completed
            """)).fetchall()

            # 逾期统计（已过期且未完成）
            overdue_count = conn.execute(text("""
                SELECT COUNT(*) AS cnt
                FROM todos
                WHERE completed = FALSE
                  AND due_date IS NOT NULL
                  AND due_date < datetime('now')
            """)).scalar()

        # 结构化聚合数据
        agg_data = {}
        for row in agg_result:
            cat = row[0]
            pri = row[1]
            cnt = row[2]
            if cat not in agg_data:
                agg_data[cat] = {"total": 0}
            agg_data[cat][pri] = cnt
            agg_data[cat]["total"] += cnt

        comp_data = {"completed": 0, "pending": 0}
        for row in completion_result:
            if row[0]:
                comp_data["completed"] = row[1]
            else:
                comp_data["pending"] = row[1]

        # ORM 方式获取计数
        total_todos = Todo.query.count()
        completed_todos = Todo.query.filter(Todo.completed == True).count()

        return jsonify({
            "hot_endpoints": hot or {},
            "total_todos": total_todos,
            "completed_todos": completed_todos,
            "overdue_count": overdue_count or 0,
            "by_category_priority": agg_data,
            "by_completion": comp_data,
            "redis_available": get_redis() is not None,
        })

    # ════════════════════════════════════════════
    # 列表接口（搜索 + 分页 + 筛选 + 排序）
    # ════════════════════════════════════════════

    @app.route("/api/todos", methods=["GET"])
    def get_todos():
        increment_visit_stat("list")

        # 有筛选/搜索/分页时跳过缓存
        has_filter = any(
            request.args.get(k) for k in (
                "completed", "priority", "category", "due_before",
                "search", "page", "per_page", "sort_by", "sort_order",
            )
        )

        cache_key = "todos:list"
        if not has_filter:
            cached = cache_get(cache_key)
            if cached is not None:
                app.logger.debug("返回缓存的待办列表")
                return jsonify(cached)

        query = Todo.query

        # ── 筛选 ──
        completed = request.args.get("completed")
        if completed is not None:
            if completed.lower() in ("true", "1"):
                query = query.filter(Todo.completed == True)
            elif completed.lower() in ("false", "0"):
                query = query.filter(Todo.completed == False)

        priority = request.args.get("priority")
        if priority and priority in VALID_PRIORITIES:
            query = query.filter(Todo.priority == priority)

        category = request.args.get("category")
        if category and category in VALID_CATEGORIES:
            query = query.filter(Todo.category == category)

        due_before = request.args.get("due_before")
        if due_before:
            parsed_date, error = parse_due_date(due_before)
            if error:
                return jsonify({"error": f"due_before 参数错误: {error}"}), 400
            query = query.filter(Todo.due_date <= parsed_date)

        # ── 全文搜索（like 模糊匹配标题和描述） ──
        search = request.args.get("search")
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Todo.title.ilike(pattern),
                    Todo.description.ilike(pattern),
                )
            )

        # ── 排序（sort_by + sort_order） ──
        sort_by = request.args.get("sort_by", "created_at")
        sort_order = request.args.get("sort_order", "desc")

        # 允许排序的列白名单（防止 SQL 注入）
        sort_columns = {
            "created_at": Todo.created_at,
            "updated_at": Todo.updated_at,
            "due_date": Todo.due_date,
            "priority": Todo.priority,
            "title": Todo.title,
        }
        sort_col = sort_columns.get(sort_by, Todo.created_at)

        if sort_order == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        # ── 分页 ──
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        per_page = max(1, min(per_page, 100))  # 限制 1-100
        page = max(1, page)

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        todos = pagination.items
        result = [todo.to_dict() for todo in todos]

        response = {
            "data": result,
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        }

        if not has_filter:
            cache_set(cache_key, response, ttl=30)

        return jsonify(response)

    # ════════════════════════════════════════════
    # 创建接口（带事务 savepoint）
    # ════════════════════════════════════════════

    @app.route("/api/todos", methods=["POST"])
    def create_todo():
        increment_visit_stat("create")

        data = request.get_json(silent=True)
        is_valid, error = validate_todo_data(data, is_create=True)
        if not is_valid:
            return jsonify({"error": error}), 400

        due_date_str = data.get("due_date")
        due_date, due_error = parse_due_date(due_date_str)
        if due_error:
            return jsonify({"error": due_error}), 400

        # ── 使用 savepoint 确保事务原子性 ──
        try:
            savepoint = db.session.begin_nested()

            todo = Todo(
                title=data["title"],
                description=data.get("description", ""),
                priority=data.get("priority", "medium"),
                category=data.get("category", "other"),
                due_date=due_date,
            )
            db.session.add(todo)

            # 创建时可附带标签
            tag_ids = data.get("tag_ids", [])
            if tag_ids:
                tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
                todo.tags = tags

            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        r = get_redis()
        if r:
            r.delete("todos:list")

        app.logger.info(f"创建待办事项: id={todo.id}, title={todo.title}")
        return jsonify(todo.to_dict()), 201

    # ════════════════════════════════════════════
    # 查询单个
    # ════════════════════════════════════════════

    @app.route("/api/todos/<int:todo_id>", methods=["GET"])
    def get_todo(todo_id):
        increment_visit_stat("detail")
        todo = Todo.query.get_or_404(todo_id)
        return jsonify(todo.to_dict())

    # ════════════════════════════════════════════
    # 更新接口
    # ════════════════════════════════════════════

    @app.route("/api/todos/<int:todo_id>", methods=["PUT"])
    def update_todo(todo_id):
        increment_visit_stat("update")
        todo = Todo.query.get_or_404(todo_id)
        data = request.get_json(silent=True)

        if not data or not isinstance(data, dict):
            return jsonify({"error": "请求体不能为空"}), 400

        is_valid, error = validate_todo_data(data, is_create=False)
        if not is_valid:
            return jsonify({"error": error}), 400

        if "title" in data:
            todo.title = data["title"]
        if "description" in data:
            todo.description = data.get("description", "")
        if "completed" in data:
            todo.completed = bool(data["completed"])
        if "priority" in data:
            todo.priority = data["priority"]
        if "category" in data:
            todo.category = data["category"]
        if "due_date" in data:
            due_date, due_error = parse_due_date(data["due_date"])
            if due_error:
                return jsonify({"error": due_error}), 400
            todo.due_date = due_date

        todo.updated_at = datetime.utcnow()
        db.session.commit()

        r = get_redis()
        if r:
            r.delete("todos:list")

        app.logger.info(f"更新待办事项: id={todo.id}")
        return jsonify(todo.to_dict())

    # ════════════════════════════════════════════
    # 删除接口（级联删除关联）
    # ════════════════════════════════════════════

    @app.route("/api/todos/<int:todo_id>", methods=["DELETE"])
    def delete_todo(todo_id):
        increment_visit_stat("delete")
        todo = Todo.query.get_or_404(todo_id)
        db.session.delete(todo)
        db.session.commit()

        r = get_redis()
        if r:
            r.delete("todos:list")

        app.logger.info(f"删除待办事项: id={todo_id}")
        return jsonify({"message": "待办事项已删除"})

    # ════════════════════════════════════════════
    # 切换完成状态
    # ════════════════════════════════════════════

    @app.route("/api/todos/<int:todo_id>/toggle", methods=["POST"])
    def toggle_todo(todo_id):
        increment_visit_stat("toggle")
        todo = Todo.query.get_or_404(todo_id)
        todo.completed = not todo.completed
        todo.updated_at = datetime.utcnow()
        db.session.commit()

        r = get_redis()
        if r:
            r.delete("todos:list")

        return jsonify(todo.to_dict())

    # ════════════════════════════════════════════
    # 批量操作：批量删除已完成
    # ════════════════════════════════════════════

    @app.route("/api/todos/batch/delete-completed", methods=["POST"])
    def batch_delete_completed():
        """批量删除所有已完成的待办事项。"""
        increment_visit_stat("batch_delete")
        deleted_count = Todo.query.filter(Todo.completed == True).delete()
        db.session.commit()

        r = get_redis()
        if r:
            r.delete("todos:list")

        app.logger.info(f"批量删除已完成事项: {deleted_count} 条")
        return jsonify({"message": f"已删除 {deleted_count} 条已完成事项", "deleted_count": deleted_count})

    # ════════════════════════════════════════════
    # 标签 CRUD
    # ════════════════════════════════════════════

    @app.route("/api/tags", methods=["GET"])
    def get_tags():
        """获取所有标签（含待办事项计数）。"""
        increment_visit_stat("tags_list")
        tags = Tag.query.order_by(Tag.name).all()
        return jsonify([tag.to_dict() for tag in tags])

    @app.route("/api/tags", methods=["POST"])
    def create_tag():
        """创建标签。"""
        increment_visit_stat("tags_create")
        data = request.get_json(silent=True)
        if not data or not data.get("name"):
            return jsonify({"error": "标签名称不能为空"}), 400

        name = data["name"].strip()
        if len(name) > 50:
            return jsonify({"error": "标签名称不能超过 50 个字符"}), 400

        if Tag.query.filter(Tag.name == name).first():
            return jsonify({"error": "标签名称已存在"}), 409

        tag = Tag(name=name, color=data.get("color", "#6c757d"))
        db.session.add(tag)
        db.session.commit()

        app.logger.info(f"创建标签: id={tag.id}, name={tag.name}")
        return jsonify(tag.to_dict()), 201

    @app.route("/api/tags/<int:tag_id>", methods=["GET"])
    def get_tag(tag_id):
        """查询单个标签及其关联的待办事项。"""
        increment_visit_stat("tags_detail")
        tag = Tag.query.get_or_404(tag_id)
        result = tag.to_dict()
        result["todos"] = [t.to_dict(include_tags=False) for t in tag.todos.all()]
        return jsonify(result)

    @app.route("/api/tags/<int:tag_id>", methods=["PUT"])
    def update_tag(tag_id):
        """更新标签名称或颜色。"""
        increment_visit_stat("tags_update")
        tag = Tag.query.get_or_404(tag_id)
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "请求体不能为空"}), 400

        if "name" in data:
            name = data["name"].strip()
            if not name or len(name) > 50:
                return jsonify({"error": "标签名称不合法"}), 400
            existing = Tag.query.filter(Tag.name == name, Tag.id != tag_id).first()
            if existing:
                return jsonify({"error": "标签名称已存在"}), 409
            tag.name = name

        if "color" in data:
            tag.color = data["color"]

        db.session.commit()
        return jsonify(tag.to_dict())

    @app.route("/api/tags/<int:tag_id>", methods=["DELETE"])
    def delete_tag(tag_id):
        """删除标签（自动解除关联）。"""
        increment_visit_stat("tags_delete")
        tag = Tag.query.get_or_404(tag_id)
        db.session.delete(tag)
        db.session.commit()
        app.logger.info(f"删除标签: id={tag_id}")
        return jsonify({"message": "标签已删除"})

    # ════════════════════════════════════════════
    # 待办 ↔ 标签 关联操作
    # ════════════════════════════════════════════

    @app.route("/api/todos/<int:todo_id>/tags", methods=["POST"])
    def assign_tags_to_todo(todo_id):
        """为待办事项添加标签（批量）。"""
        increment_visit_stat("assign_tags")
        todo = Todo.query.get_or_404(todo_id)
        data = request.get_json(silent=True)
        if not data or not data.get("tag_ids"):
            return jsonify({"error": "请提供 tag_ids 数组"}), 400

        tag_ids = data["tag_ids"]
        tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
        if not tags:
            return jsonify({"error": "未找到有效标签"}), 404

        for tag in tags:
            if tag not in todo.tags:
                todo.tags.append(tag)

        todo.updated_at = datetime.utcnow()
        db.session.commit()

        r = get_redis()
        if r:
            r.delete("todos:list")

        return jsonify(todo.to_dict())

    @app.route("/api/todos/<int:todo_id>/tags/<int:tag_id>", methods=["DELETE"])
    def remove_tag_from_todo(todo_id, tag_id):
        """移除待办事项的某个标签。"""
        increment_visit_stat("remove_tag")
        todo = Todo.query.get_or_404(todo_id)
        tag = Tag.query.get_or_404(tag_id)

        if tag not in todo.tags:
            return jsonify({"error": "该待办事项没有此标签"}), 404

        todo.tags.remove(tag)
        todo.updated_at = datetime.utcnow()
        db.session.commit()

        r = get_redis()
        if r:
            r.delete("todos:list")

        return jsonify(todo.to_dict())

    @app.route("/api/todos/<int:todo_id>/tags", methods=["PUT"])
    def set_todo_tags(todo_id):
        """覆盖设置待办事项的标签。"""
        increment_visit_stat("set_tags")
        todo = Todo.query.get_or_404(todo_id)
        data = request.get_json(silent=True)
        if not data or "tag_ids" not in data:
            return jsonify({"error": "请提供 tag_ids 数组"}), 400

        tag_ids = data["tag_ids"]
        if tag_ids:
            tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
            todo.tags = tags
        else:
            todo.tags = []

        todo.updated_at = datetime.utcnow()
        db.session.commit()

        r = get_redis()
        if r:
            r.delete("todos:list")

        return jsonify(todo.to_dict())

    # ════════════════════════════════════════════
    # 聚合统计接口（纯 SQL 复杂查询展示）
    # ════════════════════════════════════════════

    @app.route("/api/stats/dashboard", methods=["GET"])
    def dashboard_stats():
        """仪表盘：多维聚合统计（展示复杂 SQL 查询能力）。"""
        increment_visit_stat("dashboard")

        with db.engine.connect() as conn:
            # 1) 按天分组统计创建量（最近 7 天）
            daily_created = conn.execute(text("""
                SELECT
                    DATE(created_at) AS day,
                    COUNT(*) AS cnt
                FROM todos
                WHERE created_at >= date('now', '-7 days')
                GROUP BY DATE(created_at)
                ORDER BY day
            """)).fetchall()

            # 2) 按优先级分布
            priority_dist = conn.execute(text("""
                SELECT
                    priority,
                    COUNT(*) AS total,
                    SUM(CASE WHEN completed = TRUE THEN 1 ELSE 0 END) AS completed_cnt,
                    ROUND(CAST(SUM(CASE WHEN completed = TRUE THEN 1 ELSE 0 END) AS FLOAT)
                          / NULLIF(COUNT(*), 0) * 100, 1) AS completion_rate
                FROM todos
                GROUP BY priority
                ORDER BY
                    CASE priority
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 3
                    END
            """)).fetchall()

            # 3) 按分类的完成率
            category_stats = conn.execute(text("""
                SELECT
                    category,
                    COUNT(*) AS total,
                    SUM(CASE WHEN completed = TRUE THEN 1 ELSE 0 END) AS completed_cnt,
                    COUNT(CASE WHEN due_date IS NOT NULL AND due_date < datetime('now') AND completed = FALSE THEN 1 END) AS overdue_cnt
                FROM todos
                GROUP BY category
                ORDER BY total DESC
            """)).fetchall()

            # 4) 标签使用频率 TOP 10
            top_tags = conn.execute(text("""
                SELECT
                    t.name,
                    t.color,
                    COUNT(tt.todo_id) AS usage_count
                FROM tags t
                INNER JOIN todo_tags tt ON t.id = tt.tag_id
                GROUP BY t.id
                ORDER BY usage_count DESC
                LIMIT 10
            """)).fetchall()

        return jsonify({
            "daily_created": [{"day": r[0], "count": r[1]} for r in daily_created],
            "priority_distribution": [
                {
                    "priority": r[0],
                    "total": r[1],
                    "completed_cnt": r[2],
                    "completion_rate": r[3],
                }
                for r in priority_dist
            ],
            "category_stats": [
                {
                    "category": r[0],
                    "total": r[1],
                    "completed_cnt": r[2],
                    "overdue_cnt": r[3] or 0,
                }
                for r in category_stats
            ],
            "top_tags": [
                {"name": r[0], "color": r[1], "usage_count": r[2]}
                for r in top_tags
            ],
        })

    # ════════════════════════════════════════════
    # 错误处理
    # ════════════════════════════════════════════

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "请求参数有误"}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "资源未找到"}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"error": "请求方法不允许"}), 405

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.exception("服务器内部错误")
        return jsonify({"error": "服务器内部错误"}), 500

    # ════════════════════════════════════════════
    # 数据库初始化
    # ════════════════════════════════════════════

    with app.app_context():
        db.create_all()

    return app


# ──────────────────────────────────────────────
# 启动入口
# ──────────────────────────────────────────────
if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        max_retries = 30
        for retry_count in range(max_retries):
            try:
                db.create_all()
                app.logger.info("数据库表创建成功")
                break
            except Exception as e:
                app.logger.warning(f"等待数据库连接... ({retry_count + 1}/{max_retries}) - {e}")
                time.sleep(2)
        else:
            app.logger.error("数据库连接失败，已达最大重试次数")

    app.run(debug=True, host="0.0.0.0", port=5000)
else:
    app = create_app()
