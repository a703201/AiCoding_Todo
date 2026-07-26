"""新增标签功能：tags 表 + 多对多关联 + 数据迁移

迁移 ID: 002_add_tags
创建时间: 2025-07-26
描述:
    1. 创建 tags 表
    2. 创建 todo_tags 关联表
    3. 为关联表添加索引
    4. 插入默认标签数据
    5. 为已有待办事项自动分类打标
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers
revision: str = "002_add_tags"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级：创建标签相关表和数据。"""
    # ── 1. 创建 tags 表 ──
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("color", sa.String(7), server_default="#6c757d"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_tags_name", "tags", ["name"])

    # ── 2. 创建 todo_tags 关联表 ──
    op.create_table(
        "todo_tags",
        sa.Column("todo_id", sa.Integer(), sa.ForeignKey("todos.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("assigned_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ── 3. 关联表索引（加速反向查询） ──
    op.create_index("ix_todo_tags_todo_id", "todo_tags", ["todo_id"])
    op.create_index("ix_todo_tags_tag_id", "todo_tags", ["tag_id"])

    # ── 4. 插入默认标签 ──
    tags_table = sa.table(
        "tags",
        sa.column("name", sa.String),
        sa.column("color", sa.String),
    )
    op.bulk_insert(tags_table, [
        {"name": "紧急", "color": "#dc3545"},
        {"name": "学习", "color": "#0d6efd"},
        {"name": "工作", "color": "#198754"},
        {"name": "个人", "color": "#6f42c1"},
        {"name": "会议", "color": "#fd7e14"},
    ])

    # ── 5. 数据迁移：按分类自动打标签 ──
    # 使用原生 SQL 进行批量数据迁移
    conn = op.get_bind()

    # study 分类 → "学习" 标签
    conn.execute(sa.text("""
        INSERT INTO todo_tags (todo_id, tag_id)
        SELECT t.id, g.id
        FROM todos t, tags g
        WHERE t.category = 'study' AND g.name = '学习'
        AND NOT EXISTS (SELECT 1 FROM todo_tags tt WHERE tt.todo_id = t.id AND tt.tag_id = g.id)
    """))

    # work 分类 → "工作" 标签
    conn.execute(sa.text("""
        INSERT INTO todo_tags (todo_id, tag_id)
        SELECT t.id, g.id
        FROM todos t, tags g
        WHERE t.category = 'work' AND g.name = '工作'
        AND NOT EXISTS (SELECT 1 FROM todo_tags tt WHERE tt.todo_id = t.id AND tt.tag_id = g.id)
    """))

    # personal 分类 → "个人" 标签
    conn.execute(sa.text("""
        INSERT INTO todo_tags (todo_id, tag_id)
        SELECT t.id, g.id
        FROM todos t, tags g
        WHERE t.category = 'personal' AND g.name = '个人'
        AND NOT EXISTS (SELECT 1 FROM todo_tags tt WHERE tt.todo_id = t.id AND tt.tag_id = g.id)
    """))

    # high 优先级 → "紧急" 标签
    conn.execute(sa.text("""
        INSERT INTO todo_tags (todo_id, tag_id)
        SELECT t.id, g.id
        FROM todos t, tags g
        WHERE t.priority = 'high' AND g.name = '紧急'
        AND NOT EXISTS (SELECT 1 FROM todo_tags tt WHERE tt.todo_id = t.id AND tt.tag_id = g.id)
    """))


def downgrade() -> None:
    """回滚：删除关联表、标签表和数据。"""
    # ── 数据备份提示（实际回滚不备份，仅演示） ──
    op.drop_index("ix_todo_tags_tag_id")
    op.drop_index("ix_todo_tags_todo_id")
    op.drop_table("todo_tags")
    op.drop_index("ix_tags_name")
    op.drop_table("tags")
