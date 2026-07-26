"""
业务逻辑层

所有业务逻辑封装在此，通过 Repository 访问数据库。
"""
from app.services.todo_service import (
    list_todos,
    create_todo,
    get_todo_by_id,
    update_todo,
    delete_todo,
    toggle_todo,
    batch_delete_completed,
    get_stats,
    get_dashboard_stats,
    get_health_data,
    get_metrics_text,
)
from app.services.tag_service import (
    list_tags,
    create_tag,
    get_tag_by_id,
    get_tag_with_todos,
    update_tag,
    delete_tag,
    assign_tags_to_todo,
    remove_tag_from_todo,
    set_todo_tags,
)

__all__ = [
    # todo_service
    "list_todos",
    "create_todo",
    "get_todo_by_id",
    "update_todo",
    "delete_todo",
    "toggle_todo",
    "batch_delete_completed",
    "get_stats",
    "get_dashboard_stats",
    "get_health_data",
    "get_metrics_text",
    # tag_service
    "list_tags",
    "create_tag",
    "get_tag_by_id",
    "get_tag_with_todos",
    "update_tag",
    "delete_tag",
    "assign_tags_to_todo",
    "remove_tag_from_todo",
    "set_todo_tags",
]
