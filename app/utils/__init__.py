"""
工具模块

提供校验、缓存、日志等跨层工具函数。
"""
from app.utils.validators import (
    validate_todo_data,
    parse_due_date,
    validate_color,
    validate_tag_name,
    escape_like_pattern,
)
from app.utils.cache import (
    cache_get,
    cache_set,
    cache_delete,
    invalidate_todo_cache,
    increment_visit_stat,
    get_hot_stats,
)
from app.utils.logging import setup_logging

__all__ = [
    # validators
    "validate_todo_data",
    "parse_due_date",
    "validate_color",
    "validate_tag_name",
    "escape_like_pattern",
    # cache
    "cache_get",
    "cache_set",
    "cache_delete",
    "invalidate_todo_cache",
    "increment_visit_stat",
    "get_hot_stats",
    # logging
    "setup_logging",
]
