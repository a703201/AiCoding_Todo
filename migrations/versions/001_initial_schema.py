"""初始数据库结构：todos 表 + 索引

迁移 ID: 001_initial_schema
创建时间: 2025-07-26
描述: 创建待办事项核心表，包含基础字段和单列索引
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级：创建 todos 表与基础索引。"""
    # ── 创建 todos 表 ──
    op.create_table(
        "todos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("completed", sa.Boolean(), server_default=sa.text("FALSE")),
        sa.Column("priority", sa.String(20), server_default="medium"),
        sa.Column("category", sa.String(20), server_default="other"),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ── 单列索引（加速常用筛选与排序） ──
    op.create_index("ix_todos_title", "todos", ["title"])
    op.create_index("ix_todos_completed", "todos", ["completed"])
    op.create_index("ix_todos_priority", "todos", ["priority"])
    op.create_index("ix_todos_due_date", "todos", ["due_date"])
    op.create_index("ix_todos_created_at", "todos", ["created_at"])

    # ── 复合索引（覆盖高频组合筛选） ──
    op.create_index("ix_todos_completed_priority", "todos", ["completed", "priority"])
    op.create_index("ix_todos_category_priority", "todos", ["category", "priority"])


def downgrade() -> None:
    """回滚：删除所有索引和表。"""
    op.drop_index("ix_todos_category_priority")
    op.drop_index("ix_todos_completed_priority")
    op.drop_index("ix_todos_created_at")
    op.drop_index("ix_todos_due_date")
    op.drop_index("ix_todos_priority")
    op.drop_index("ix_todos_completed")
    op.drop_index("ix_todos_title")
    op.drop_table("todos")
