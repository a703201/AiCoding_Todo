"""
请求校验辅助函数

集中管理所有输入校验逻辑，确保 API 层和 Service 层复用同一套规则。
"""
from datetime import datetime
from typing import Optional, Tuple

from flask import current_app


def validate_todo_data(data: dict, is_create: bool = False) -> Tuple[bool, Optional[str]]:
    """校验待办事项输入。

    Args:
        data: 请求 JSON 数据
        is_create: 是否为创建操作（创建时 title 必填）

    Returns:
        (is_valid, error_message)
    """
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
        min_len = current_app.config.get("TITLE_MIN_LENGTH", 1)
        max_len = current_app.config.get("TITLE_MAX_LENGTH", 200)
        if len(stripped) < min_len:
            return False, f"标题长度至少 {min_len} 个字符"
        if len(stripped) > max_len:
            return False, f"标题长度不能超过 {max_len} 个字符"
        data["title"] = stripped

    valid_priorities = current_app.config.get("VALID_PRIORITIES", {"low", "medium", "high"})
    if "priority" in data and data["priority"] is not None:
        if data["priority"] not in valid_priorities:
            return False, f"优先级必须为: {', '.join(sorted(valid_priorities))}"

    valid_categories = current_app.config.get("VALID_CATEGORIES", {"personal", "work", "study", "health", "other"})
    if "category" in data and data["category"] is not None:
        if data["category"] not in valid_categories:
            return False, f"分类必须为: {', '.join(sorted(valid_categories))}"

    return True, None


def parse_due_date(value) -> Tuple[Optional[datetime], Optional[str]]:
    """解析 ISO 格式日期字符串。

    Returns:
        (parsed_datetime_or_None, error_message_or_None)
    """
    if value is None:
        return None, None
    if not isinstance(value, str):
        return None, "截止日期必须是 ISO 格式的字符串"
    try:
        return datetime.fromisoformat(value), None
    except (ValueError, TypeError):
        return None, "截止日期格式无效，请使用 ISO 格式（如 2025-07-26T12:00:00）"


def validate_color(color) -> Tuple[bool, Optional[str]]:
    """校验颜色值是否为合法 hex 格式。

    Returns:
        (is_valid, error_message_or_None)
    """
    if not isinstance(color, str) or not color.startswith("#") or len(color) not in (4, 7):
        return False, "颜色格式无效，请使用 hex 格式如 #6c757d"
    return True, None


def validate_tag_name(name: str, max_length: int = 50) -> Tuple[bool, Optional[str]]:
    """校验标签名称。

    Returns:
        (is_valid, error_message_or_None)
    """
    if not name or not isinstance(name, str):
        return False, "标签名称不能为空"
    stripped = name.strip()
    if not stripped:
        return False, "标签名称不能为空"
    if len(stripped) > max_length:
        return False, f"标签名称不能超过 {max_length} 个字符"
    return True, None


def escape_like_pattern(pattern: str) -> str:
    """转义 LIKE 查询中的通配符，防止意外模式匹配。"""
    return pattern.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
