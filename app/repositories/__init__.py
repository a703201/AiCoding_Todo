"""
数据访问层（Repository 模式）

封装所有 ORM 操作，Service 层通过 Repository 访问数据库，
便于单元测试 mock 和未来切换数据源。
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, case, func, or_, text

from app.extensions import db
from app.models import Todo, Tag, todo_tags
from app.exceptions import NotFoundException, ConflictException

import logging
logger = logging.getLogger(__name__)


# ════════════════════════════════════════════
# Todo Repository
# ════════════════════════════════════════════


class TodoRepository:
    """Todo 数据访问对象。"""

    @staticmethod
    def find_all(
        completed: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        due_before: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[List[Todo], Dict[str, Any]]:
        """分页查询 Todo 列表（含筛选、搜索、排序）。

        Returns:
            (todos, pagination_meta)
        """
        query = Todo.query

        # 筛选
        if completed is not None:
            if completed.lower() in ("true", "1"):
                query = query.filter(Todo.completed == True)
            elif completed.lower() in ("false", "0"):
                query = query.filter(Todo.completed == False)

        if priority is not None:
            query = query.filter(Todo.priority == priority)

        if category is not None:
            query = query.filter(Todo.category == category)

        if due_before:
            from app.utils.validators import parse_due_date
            parsed_date, _ = parse_due_date(due_before)
            if parsed_date:
                query = query.filter(Todo.due_date <= parsed_date)

        # 搜索
        if search and search.strip():
            from app.utils.validators import escape_like_pattern
            escaped = escape_like_pattern(search.strip())
            pattern = f"%{escaped}%"
            query = query.filter(
                or_(Todo.title.ilike(pattern), Todo.description.ilike(pattern))
            )

        # 排序
        sort_columns = {
            "created_at": Todo.created_at,
            "updated_at": Todo.updated_at,
            "due_date": Todo.due_date,
            "title": Todo.title,
        }
        sort_col = sort_columns.get(sort_by)

        if sort_by == "priority":
            priority_case = case(
                (Todo.priority == "high", 1),
                (Todo.priority == "medium", 2),
                (Todo.priority == "low", 3),
                else_=4,
            )
            if sort_order == "asc":
                query = query.order_by(priority_case.asc())
            else:
                query = query.order_by(priority_case.desc())
        elif sort_col is not None:
            if sort_order == "asc":
                query = query.order_by(sort_col.asc())
            else:
                query = query.order_by(sort_col.desc())
        else:
            logger.warning("sort_by 参数无效，回退到默认排序 created_at desc")
            query = query.order_by(Todo.created_at.desc())

        # 分页
        per_page = max(1, min(per_page, 100))
        page = max(1, page)

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        pagination_meta = {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        }

        return pagination.items, pagination_meta

    @staticmethod
    def find_by_id(todo_id: int) -> Optional[Todo]:
        """按 ID 查询单个 Todo。"""
        return db.session.get(Todo, todo_id)

    @staticmethod
    def find_by_id_or_404(todo_id: int) -> Todo:
        """按 ID 查询，不存在则抛 NotFoundException。"""
        todo = db.session.get(Todo, todo_id)
        if todo is None:
            raise NotFoundException("待办事项未找到")
        return todo

    @staticmethod
    def create(todo: Todo) -> Todo:
        """持久化 Todo 实例。"""
        db.session.add(todo)
        db.session.commit()
        return todo

    @staticmethod
    def save(todo: Todo) -> Todo:
        """保存已有 Todo 的变更。"""
        todo.updated_at = datetime.utcnow()
        db.session.commit()
        return todo

    @staticmethod
    def delete(todo: Todo) -> None:
        """删除 Todo 实例。"""
        db.session.delete(todo)
        db.session.commit()

    @staticmethod
    def delete_completed() -> int:
        """批量删除已完成的 Todo，返回删除数。"""
        deleted = Todo.query.filter(Todo.completed == True).delete()
        db.session.commit()
        return deleted

    @staticmethod
    def count() -> int:
        """Todo 总数。"""
        return Todo.query.count()

    @staticmethod
    def count_completed() -> int:
        """已完成 Todo 数。"""
        return Todo.query.filter(Todo.completed == True).count()

    @staticmethod
    def count_by_priority(priority: str) -> int:
        """按优先级统计。"""
        return Todo.query.filter(Todo.priority == priority).count()

    @staticmethod
    def begin_savepoint():
        """开启嵌套事务 savepoint。"""
        return db.session.begin_nested()

    @staticmethod
    def rollback():
        """回滚当前事务。"""
        db.session.rollback()

    @staticmethod
    def commit():
        """提交当前事务。"""
        db.session.commit()

    # ── 聚合查询 ──

    @staticmethod
    def agg_by_category_priority() -> List:
        """按分类+优先级聚合。"""
        return db.session.execute(text("""
            SELECT category, priority, COUNT(*) AS cnt
            FROM todos
            GROUP BY category, priority
            ORDER BY category, priority
        """)).fetchall()

    @staticmethod
    def agg_by_completion() -> List:
        """按完成状态聚合。"""
        return db.session.execute(text("""
            SELECT completed, COUNT(*) AS cnt
            FROM todos
            GROUP BY completed
        """)).fetchall()

    @staticmethod
    def count_overdue() -> int:
        """统计逾期未完成任务数。"""
        return db.session.execute(text("""
            SELECT COUNT(*) AS cnt
            FROM todos
            WHERE completed = FALSE
              AND due_date IS NOT NULL
              AND due_date < :now
        """), {"now": datetime.utcnow()}).scalar() or 0

    @staticmethod
    def daily_created_since(days: int = 7) -> List:
        """最近 N 天每日创建统计。"""
        since = datetime.utcnow() - timedelta(days=days)
        return db.session.execute(text("""
            SELECT DATE(created_at) AS day, COUNT(*) AS cnt
            FROM todos
            WHERE created_at >= :since
            GROUP BY DATE(created_at)
            ORDER BY day
        """), {"since": since}).fetchall()

    @staticmethod
    def priority_distribution() -> List:
        """优先级分布（含完成率）。"""
        return db.session.execute(text("""
            SELECT
                priority, COUNT(*) AS total,
                SUM(CASE WHEN completed = TRUE THEN 1 ELSE 0 END) AS completed_cnt,
                ROUND(CAST(SUM(CASE WHEN completed = TRUE THEN 1 ELSE 0 END) AS FLOAT)
                      / NULLIF(COUNT(*), 0) * 100, 1) AS completion_rate
            FROM todos
            GROUP BY priority
            ORDER BY CASE priority
                WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3
            END
        """)).fetchall()

    @staticmethod
    def category_stats() -> List:
        """分类统计（含逾期数）。"""
        return db.session.execute(text("""
            SELECT
                category, COUNT(*) AS total,
                SUM(CASE WHEN completed = TRUE THEN 1 ELSE 0 END) AS completed_cnt,
                COUNT(CASE WHEN due_date IS NOT NULL AND due_date < :now AND completed = FALSE THEN 1 END) AS overdue_cnt
            FROM todos
            GROUP BY category
            ORDER BY total DESC
        """), {"now": datetime.utcnow()}).fetchall()


# ════════════════════════════════════════════
# Tag Repository
# ════════════════════════════════════════════


class TagRepository:
    """Tag 数据访问对象。"""

    @staticmethod
    def find_all() -> List[Tag]:
        """获取所有标签（按名称排序）。"""
        return Tag.query.order_by(Tag.name).all()

    @staticmethod
    def find_by_id(tag_id: int) -> Optional[Tag]:
        """按 ID 查询标签。"""
        return db.session.get(Tag, tag_id)

    @staticmethod
    def find_by_id_or_404(tag_id: int) -> Tag:
        """按 ID 查询标签，不存在则抛 NotFoundException。"""
        tag = db.session.get(Tag, tag_id)
        if tag is None:
            raise NotFoundException("标签未找到")
        return tag

    @staticmethod
    def find_by_name(name: str) -> Optional[Tag]:
        """按名称查询标签。"""
        return Tag.query.filter(Tag.name == name).first()

    @staticmethod
    def find_by_name_excluding(name: str, exclude_id: int) -> Optional[Tag]:
        """查询同名标签（排除指定 ID）。"""
        return Tag.query.filter(Tag.name == name, Tag.id != exclude_id).first()

    @staticmethod
    def find_by_ids(tag_ids: List[int]) -> List[Tag]:
        """批量按 ID 查询。"""
        return Tag.query.filter(Tag.id.in_(tag_ids)).all()

    @staticmethod
    def create(tag: Tag) -> Tag:
        """持久化 Tag 实例。"""
        db.session.add(tag)
        db.session.commit()
        return tag

    @staticmethod
    def save(tag: Tag) -> Tag:
        """保存已有 Tag 的变更。"""
        db.session.commit()
        return tag

    @staticmethod
    def delete(tag: Tag) -> None:
        """删除 Tag 实例。"""
        db.session.delete(tag)
        db.session.commit()

    @staticmethod
    def count() -> int:
        """Tag 总数。"""
        return Tag.query.count()

    @staticmethod
    def tag_usage_counts() -> Dict[int, int]:
        """标签使用量聚合（返回 {tag_id: count}）。"""
        from sqlalchemy import func as sa_func
        rows = (
            db.session.query(todo_tags.c.tag_id, sa_func.count(todo_tags.c.todo_id))
            .group_by(todo_tags.c.tag_id)
            .all()
        )
        return dict(rows)

    @staticmethod
    def top_tags(limit: int = 10) -> List:
        """使用频率最高的标签。"""
        return db.session.execute(text("""
            SELECT t.name, t.color, COUNT(tt.todo_id) AS usage_count
            FROM tags t
            INNER JOIN todo_tags tt ON t.id = tt.tag_id
            GROUP BY t.id
            ORDER BY usage_count DESC
            LIMIT :limit
        """), {"limit": limit}).fetchall()
