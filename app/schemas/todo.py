"""
Todo 序列化 Schema

职责：
- TodoCreateSchema / TodoUpdateSchema: 输入数据转换
- TodoOutSchema: 输出格式化（从 ORM 模型转换为 dict）
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


# TODO: v1.5 迁移到 API 层使用此 Schema 进行输入校验
@dataclass
class TodoCreateSchema:
    """创建 Todo 的输入 Schema。"""

    title: str
    description: str = ""
    priority: str = "medium"
    category: str = "other"
    due_date: Optional[str] = None
    tag_ids: List[int] = field(default_factory=list)

    def to_service_dict(self) -> Dict[str, Any]:
        """转换为 Service 层接受的字典格式。"""
        return {
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "category": self.category,
            "due_date": self.due_date,
            "tag_ids": self.tag_ids,
        }


# TODO: v1.5 迁移到 API 层使用此 Schema 进行输入校验
@dataclass
class TodoUpdateSchema:
    """更新 Todo 的输入 Schema。"""

    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    due_date: Optional[str] = None

    def to_service_dict(self) -> Dict[str, Any]:
        """转换为 Service 层接受的字典格式（仅包含非 None 字段）。"""
        result: Dict[str, Any] = {}
        if self.title is not None:
            result["title"] = self.title
        if self.description is not None:
            result["description"] = self.description
        if self.completed is not None:
            result["completed"] = self.completed
        if self.priority is not None:
            result["priority"] = self.priority
        if self.category is not None:
            result["category"] = self.category
        if self.due_date is not None:
            result["due_date"] = self.due_date
        return result


@dataclass
class TodoOutSchema:
    """Todo 输出 Schema —— 将 ORM 模型转为标准 dict。"""

    @staticmethod
    def from_model(todo) -> Dict[str, Any]:
        """从 ORM Todo 对象生成输出 dict。

        Args:
            todo: ORM Todo 实例

        Returns:
            标准化的输出字典
        """
        return {
            "id": todo.id,
            "title": todo.title,
            "description": todo.description or "",
            "completed": todo.completed,
            "priority": todo.priority,
            "category": todo.category,
            "due_date": todo.due_date.isoformat() if todo.due_date else None,
            "created_at": todo.created_at.isoformat() if todo.created_at else None,
            "updated_at": todo.updated_at.isoformat() if todo.updated_at else None,
            "tags": [
                TagOutSchema.from_model(tag) for tag in (todo.tags or [])
            ],
        }


# 避免循环导入：延迟导入 TagOutSchema
from app.schemas.tag import TagOutSchema
