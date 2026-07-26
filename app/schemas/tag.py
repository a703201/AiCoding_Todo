"""
Tag 序列化 Schema
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional


# TODO: v1.5 迁移到 API 层使用此 Schema 进行输入校验
@dataclass
class TagCreateSchema:
    """创建 Tag 的输入 Schema。"""

    name: str
    color: str = "#6c757d"

    def to_service_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "color": self.color}


# TODO: v1.5 迁移到 API 层使用此 Schema 进行输入校验
@dataclass
class TagUpdateSchema:
    """更新 Tag 的输入 Schema。"""

    name: Optional[str] = None
    color: Optional[str] = None

    def to_service_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if self.name is not None:
            result["name"] = self.name
        if self.color is not None:
            result["color"] = self.color
        return result


@dataclass
class TagOutSchema:
    """Tag 输出 Schema。"""

    @staticmethod
    def from_model(tag, include_todos: bool = False, todo_count_override: Optional[int] = None) -> Dict[str, Any]:
        """从 ORM Tag 对象生成输出 dict。

        Args:
            tag: ORM Tag 实例
            include_todos: 是否包含关联的 Todo 列表
            todo_count_override: 外部传入的计数，避免 N+1 查询

        Returns:
            标准化的输出字典
        """
        if todo_count_override is not None:
            count = todo_count_override
        else:
            count = len(tag.todos.all()) if tag.todos else 0

        result: Dict[str, Any] = {
            "id": tag.id,
            "name": tag.name,
            "color": tag.color,
            "created_at": tag.created_at.isoformat() if tag.created_at else None,
            "todo_count": count,
        }
        if include_todos:
            # 延迟导入避免循环依赖
            from app.schemas.todo import TodoOutSchema
            result["todos"] = [
                TodoOutSchema.from_model(t) for t in tag.todos
            ]
        return result
