"""
待办事项数据模型
"""
from datetime import datetime

from sqlalchemy import Index

from app.extensions import db
from app.models.tag import todo_tags


class Todo(db.Model):
    """待办事项模型。

    字段:
        id, title, description, completed, priority,
        category, due_date, created_at, updated_at

    关联:
        tags (M:N → Tag)
    """

    __tablename__ = "todos"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
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

    # ── 表级索引 ──
    __table_args__ = (
        Index("ix_todos_title", "title"),
        Index("ix_todos_completed", "completed"),
        Index("ix_todos_priority", "priority"),
        Index("ix_todos_completed_priority", "completed", "priority"),
        Index("ix_todos_category_priority", "category", "priority"),
        Index("ix_todos_due_date", "due_date"),
        Index("ix_todos_created_at", "created_at"),
    )

    def to_dict(self, include_tags: bool = True) -> dict:
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
