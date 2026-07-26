"""
序列化 Schema 层

使用 dataclass 定义 API 输入/输出结构，与 ORM 模型解耦。
"""
from app.schemas.todo import TodoCreateSchema, TodoUpdateSchema, TodoOutSchema
from app.schemas.tag import TagCreateSchema, TagUpdateSchema, TagOutSchema

__all__ = [
    "TodoCreateSchema",
    "TodoUpdateSchema",
    "TodoOutSchema",
    "TagCreateSchema",
    "TagUpdateSchema",
    "TagOutSchema",
]
