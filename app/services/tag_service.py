"""
标签业务逻辑层

所有 Tag 相关的业务规则封装在此。
数据访问通过 Repository 层完成。
"""
import logging
from typing import Dict, List, Optional

from app.models import Tag, Todo
from app.repositories import TagRepository, TodoRepository
from app.exceptions import ConflictException, ValidationException, NotFoundException
from app.schemas.tag import TagOutSchema

logger = logging.getLogger(__name__)


def list_tags() -> List[Dict]:
    """获取所有标签（含待办事项计数，批量聚合避免 N+1）。"""
    tags = TagRepository.find_all()
    counts = TagRepository.tag_usage_counts()

    result = []
    for tag in tags:
        d = TagOutSchema.from_model(tag, todo_count_override=counts.get(tag.id, 0))
        result.append(d)
    return result


def create_tag(name: str, color: str = "#6c757d") -> Tag:
    """创建标签。

    Raises:
        ConflictException: 名称重复时
    """
    existing = TagRepository.find_by_name(name)
    if existing:
        raise ConflictException("标签名称已存在")

    tag = Tag(name=name, color=color)
    tag = TagRepository.create(tag)

    logger.info(f"创建标签: id={tag.id}, name={tag.name}")
    return tag


def get_tag_by_id(tag_id: int) -> Optional[Tag]:
    """按 ID 查询标签。"""
    return TagRepository.find_by_id(tag_id)


def get_tag_or_404(tag_id: int) -> Tag:
    """按 ID 查询，不存在则抛 NotFoundException。"""
    return TagRepository.find_by_id_or_404(tag_id)


def get_tag_with_todos(tag_id: int) -> Optional[Dict]:
    """查询单个标签及其关联的待办事项。

    Returns:
        包含标签信息和关联待办列表的字典，或 None
    """
    tag = TagRepository.find_by_id(tag_id)
    if tag is None:
        return None
    return TagOutSchema.from_model(tag, include_todos=True)


def update_tag(tag: Tag, data: dict) -> Tag:
    """更新标签名称或颜色。

    Raises:
        ConflictException: 名称重复时
    """
    if "name" in data:
        name = data["name"].strip()
        existing = TagRepository.find_by_name_excluding(name, tag.id)
        if existing:
            raise ConflictException("标签名称已存在")
        tag.name = name

    if "color" in data:
        tag.color = data["color"]

    return TagRepository.save(tag)


def delete_tag(tag: Tag) -> None:
    """删除标签（自动解除关联）。"""
    TagRepository.delete(tag)
    logger.info(f"删除标签: id={tag.id}")


def assign_tags_to_todo(todo: Todo, tag_ids: List[int]) -> Todo:
    """为待办事项添加标签（批量）。

    Raises:
        ValidationException: 标签不存在时
    """
    tags = TagRepository.find_by_ids(tag_ids)
    if not tags:
        raise ValidationException("未找到有效标签")

    found_ids = {t.id for t in tags}
    missing = [tid for tid in tag_ids if tid not in found_ids]
    if missing:
        raise ValidationException(f"标签不存在: {missing}")

    for tag in tags:
        if tag not in todo.tags:
            todo.tags.append(tag)

    todo = TodoRepository.save(todo)

    from app.utils.cache import invalidate_todo_cache
    invalidate_todo_cache()
    return todo


def remove_tag_from_todo(todo: Todo, tag: Tag) -> Todo:
    """移除待办事项的某个标签。

    Raises:
        NotFoundException: 待办事项没有此标签时
    """
    if tag not in todo.tags:
        raise NotFoundException("该待办事项没有此标签")

    todo.tags.remove(tag)
    todo = TodoRepository.save(todo)

    from app.utils.cache import invalidate_todo_cache
    invalidate_todo_cache()
    return todo


def set_todo_tags(todo: Todo, tag_ids: List[int]) -> Todo:
    """覆盖设置待办事项的标签。

    Raises:
        ValidationException: 标签不存在时
    """
    if tag_ids:
        tags = TagRepository.find_by_ids(tag_ids)
        found_ids = {t.id for t in tags}
        missing = [tid for tid in tag_ids if tid not in found_ids]
        if missing:
            raise ValidationException(f"标签不存在: {missing}")
        todo.tags = tags
    else:
        todo.tags = []

    todo = TodoRepository.save(todo)

    from app.utils.cache import invalidate_todo_cache
    invalidate_todo_cache()
    return todo
