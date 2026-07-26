"""
待办事项业务逻辑层

所有 Todo 相关的业务规则封装在此。
数据访问通过 Repository 层完成，API 层仅负责 HTTP 请求/响应转换。
"""
import logging
import os
import platform
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text

from app.extensions import db
from app.models import Todo, Tag
from app.repositories import TodoRepository, TagRepository
from app.exceptions import ValidationException, NotFoundException
from app.schemas.todo import TodoOutSchema
from app.schemas.tag import TagOutSchema
from app.utils.cache import invalidate_todo_cache
from app.utils.validators import parse_due_date, escape_like_pattern

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore

logger = logging.getLogger(__name__)


def list_todos(
    completed: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    due_before: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    per_page: int = 20,
) -> Tuple[List[Dict], Dict]:
    """获取待办列表（搜索 + 分页 + 筛选 + 排序 + 缓存）。

    Returns:
        (todo_dicts, pagination_meta)

    Raises:
        ValidationException: 筛选参数无效时
    """
    # ── 参数校验 ──
    if completed is not None and completed.lower() not in ("true", "1", "false", "0"):
        raise ValidationException(f"completed 参数无效: {completed}（仅接受 true/false/0/1）")

    if priority is not None and priority not in {"low", "medium", "high"}:
        raise ValidationException(f"priority 参数无效: {priority}（仅接受 low/medium/high）")

    if category is not None and category not in {"personal", "work", "study", "health", "other"}:
        raise ValidationException(f"category 参数无效: {category}（仅接受 personal/work/study/health/other）")

    if due_before:
        parsed_date, error = parse_due_date(due_before)
        if error:
            raise ValidationException(f"due_before 参数错误: {error}")

    # ── 委托 Repository 查询 ──
    todos, pagination_meta = TodoRepository.find_all(
        completed=completed,
        priority=priority,
        category=category,
        due_before=due_before,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page,
    )

    result = [TodoOutSchema.from_model(todo) for todo in todos]
    return result, pagination_meta


def create_todo(data: dict) -> Todo:
    """创建待办事项（含 savepoint 事务 + 标签校验）。

    Raises:
        ValidationException: 输入无效或标签不存在时
    """
    due_date_str = data.get("due_date")
    due_date, due_error = parse_due_date(due_date_str)
    if due_error:
        raise ValidationException(due_error)

    try:
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
            tags = TagRepository.find_by_ids(tag_ids)
            found_ids = {t.id for t in tags}
            missing = [tid for tid in tag_ids if tid not in found_ids]
            if missing:
                TodoRepository.rollback()
                raise ValidationException(f"标签不存在: {missing}")
            todo.tags = tags

        TodoRepository.commit()
    except ValidationException:
        raise
    except Exception:
        TodoRepository.rollback()
        raise

    invalidate_todo_cache()
    logger.info(f"创建待办事项: id={todo.id}")
    return todo


def get_todo_by_id(todo_id: int) -> Optional[Todo]:
    """按 ID 查询单个待办事项。"""
    return TodoRepository.find_by_id(todo_id)


def get_todo_or_404(todo_id: int) -> Todo:
    """按 ID 查询，不存在则抛 NotFoundException。"""
    return TodoRepository.find_by_id_or_404(todo_id)


def update_todo(todo: Todo, data: dict) -> Todo:
    """更新待办事项。

    Raises:
        ValidationException: 输入无效时
    """
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
            raise ValidationException(due_error)
        todo.due_date = due_date

    todo = TodoRepository.save(todo)
    invalidate_todo_cache()
    logger.info(f"更新待办事项: id={todo.id}")
    return todo


def delete_todo(todo: Todo) -> None:
    """删除待办事项（级联删除关联）。"""
    TodoRepository.delete(todo)
    invalidate_todo_cache()
    logger.info(f"删除待办事项: id={todo.id}")


def toggle_todo(todo: Todo) -> Todo:
    """切换完成状态。"""
    todo.completed = not todo.completed
    todo = TodoRepository.save(todo)
    invalidate_todo_cache()
    return todo


def batch_delete_completed() -> int:
    """批量删除所有已完成的待办事项。

    Returns:
        删除数量
    """
    deleted_count = TodoRepository.delete_completed()
    invalidate_todo_cache()
    logger.info(f"批量删除已完成事项: {deleted_count} 条")
    return deleted_count


def get_stats() -> Dict[str, Any]:
    """获取聚合统计数据。"""
    from app.utils.cache import get_hot_stats
    hot = get_hot_stats()

    agg_result = TodoRepository.agg_by_category_priority()
    completion_result = TodoRepository.agg_by_completion()
    overdue_count = TodoRepository.count_overdue()

    agg_data: Dict[str, Dict] = {}
    for row in agg_result:
        cat, pri, cnt = row[0], row[1], row[2]
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

    total_todos = TodoRepository.count()
    completed_todos = TodoRepository.count_completed()

    from app.extensions import get_redis
    return {
        "hot_endpoints": hot or {},
        "total_todos": total_todos,
        "completed_todos": completed_todos,
        "overdue_count": overdue_count,
        "by_category_priority": agg_data,
        "by_completion": comp_data,
        "redis_available": get_redis() is not None,
    }


def get_dashboard_stats() -> Dict[str, Any]:
    """获取仪表盘多维统计。"""
    daily_created = TodoRepository.daily_created_since(days=7)
    priority_dist = TodoRepository.priority_distribution()
    category_stats_rows = TodoRepository.category_stats()
    top_tags = TagRepository.top_tags(limit=10)

    return {
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
            for r in category_stats_rows
        ],
        "top_tags": [
            {"name": r[0], "color": r[1], "usage_count": r[2]}
            for r in top_tags
        ],
    }


def get_health_data() -> Tuple[Dict[str, Any], int]:
    """获取增强健康检查数据。

    Returns:
        (health_dict, http_status_code)
    """
    health_data = {"status": "ok"}

    # 数据库连通性
    try:
        db.session.execute(text("SELECT 1"))
        health_data["database"] = "ok"
    except Exception:
        health_data["database"] = "error"
        health_data["status"] = "degraded"

    # Redis 连通性
    from app.extensions import get_redis
    r = get_redis()
    health_data["redis"] = "ok" if r else "unavailable"

    # 资源监控（阈值可配置）
    disk_threshold = float(os.environ.get("HEALTH_DISK_THRESHOLD", "90"))
    mem_threshold = float(os.environ.get("HEALTH_MEM_THRESHOLD", "95"))

    try:
        disk_usage = psutil.disk_usage("/")
        health_data["disk_usage_percent"] = disk_usage.percent
        if disk_usage.percent > disk_threshold:
            health_data["status"] = "degraded"
    except Exception:
        health_data["disk_usage_percent"] = "unknown"

    try:
        mem = psutil.virtual_memory()
        health_data["memory_usage_percent"] = mem.percent
        if mem.percent > mem_threshold:
            health_data["status"] = "degraded"
    except Exception:
        health_data["memory_usage_percent"] = "unknown"

    # 业务数据统计
    try:
        health_data["total_todos"] = TodoRepository.count()
        health_data["total_tags"] = TagRepository.count()
    except Exception:
        pass

    http_status = 200 if health_data["status"] == "ok" else 503
    return health_data, http_status


def get_metrics_text() -> str:
    """生成 Prometheus 格式的指标文本。"""
    lines = []

    # 应用信息
    lines.append("# HELP todo_app_info 待办事项应用信息")
    lines.append("# TYPE todo_app_info gauge")
    lines.append(f'todo_app_info{{version="1.4.0",python="{platform.python_version()}"}} 1')

    # 待办计数
    total = TodoRepository.count()
    completed = TodoRepository.count_completed()
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

    # 优先级分布
    lines.append("# HELP todo_by_priority 按优先级分布")
    lines.append("# TYPE todo_by_priority gauge")
    for p in ("low", "medium", "high"):
        count = TodoRepository.count_by_priority(p)
        lines.append(f'todo_by_priority{{priority="{p}"}} {count}')

    # 标签总数
    tag_count = TagRepository.count()
    lines.append("# HELP todo_tags_total 标签总数")
    lines.append("# TYPE todo_tags_total gauge")
    lines.append(f"todo_tags_total {tag_count}")

    # 系统资源
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

    # Redis 可用性
    from app.extensions import get_redis
    r = get_redis()
    lines.append("# HELP redis_available Redis 可用性 (1=可用, 0=不可用)")
    lines.append("# TYPE redis_available gauge")
    lines.append(f"redis_available {1 if r else 0}")

    return "\n".join(lines) + "\n"
