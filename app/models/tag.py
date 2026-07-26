"""
标签数据模型 + 多对多关联表
"""
from datetime import datetime

from sqlalchemy import Index

from app.extensions import db

# ── 多对多关联表 ──
todo_tags = db.Table(
    "todo_tags",
    db.Column("todo_id", db.Integer, db.ForeignKey("todos.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    db.Column("assigned_at", db.DateTime, default=datetime.utcnow),
)

# 关联表索引（在 Table 对象创建后单独定义）
db.Index("ix_todo_tags_todo_id", todo_tags.c.todo_id)
db.Index("ix_todo_tags_tag_id", todo_tags.c.tag_id)


class Tag(db.Model):
    """标签模型。

    与 Todo 为多对多关系。
    字段:
        id, name, color, created_at
    """

    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    color = db.Column(db.String(7), default="#6c757d")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_tags_name", "name"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "todo_count": len(self.todos.all()) if self.todos else 0,
        }
