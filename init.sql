-- =============================================
-- 待办事项应用 - 完整数据库初始化脚本
-- 仅在容器首次启动、数据卷为空时执行
-- =============================================
-- 数据库编码: UTF-8
-- 方言: PostgreSQL
-- =============================================
-- ⚠️ 注意：
--   本文件仅供 Docker Compose 首次启动时自动初始化数据库。
--   正式环境的数据库迁移请使用 Alembic（`flask db upgrade`），
--   迁移文件位于 migrations/versions/ 目录。
--   若两者冲突，以 Alembic 迁移为准。
--   两个文件中表结构应当保持同步，如有修改请同时更新。
-- =============================================

-- ════════════════════════════════════════════
-- 1. 创建表
-- ════════════════════════════════════════════

-- 待办事项表
CREATE TABLE IF NOT EXISTS todos (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '',
    completed   BOOLEAN DEFAULT FALSE,
    priority    VARCHAR(20) DEFAULT 'medium'
                    CHECK (priority IN ('low', 'medium', 'high')),
    category    VARCHAR(20) DEFAULT 'other'
                    CHECK (category IN ('personal', 'work', 'study', 'health', 'other')),
    due_date    TIMESTAMP,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 标签表
CREATE TABLE IF NOT EXISTS tags (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(50) NOT NULL UNIQUE,
    color       VARCHAR(7) DEFAULT '#6c757d',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 待办事项-标签关联表（多对多）
CREATE TABLE IF NOT EXISTS todo_tags (
    todo_id     INTEGER NOT NULL REFERENCES todos(id) ON DELETE CASCADE,
    tag_id      INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (todo_id, tag_id)
);

-- ════════════════════════════════════════════
-- 2. 创建索引（优化查询性能）
-- ════════════════════════════════════════════

-- 单列索引
CREATE INDEX IF NOT EXISTS idx_todos_completed   ON todos(completed);
CREATE INDEX IF NOT EXISTS idx_todos_priority    ON todos(priority);
CREATE INDEX IF NOT EXISTS idx_todos_title       ON todos(title);
CREATE INDEX IF NOT EXISTS idx_todos_due_date    ON todos(due_date);
CREATE INDEX IF NOT EXISTS idx_todos_created_at  ON todos(created_at);

-- 复合索引（覆盖高频筛选组合）
CREATE INDEX IF NOT EXISTS idx_todos_completed_priority
    ON todos(completed, priority);
CREATE INDEX IF NOT EXISTS idx_todos_category_priority
    ON todos(category, priority);

-- 标签关联表索引（加速反向查询）
CREATE INDEX IF NOT EXISTS idx_todo_tags_todo_id ON todo_tags(todo_id);
CREATE INDEX IF NOT EXISTS idx_todo_tags_tag_id  ON todo_tags(tag_id);

-- 标签名称唯一索引
CREATE UNIQUE INDEX IF NOT EXISTS idx_tags_name  ON tags(name);

-- ════════════════════════════════════════════
-- 3. 初始化示例数据
-- ════════════════════════════════════════════

INSERT INTO tags (name, color) VALUES
    ('紧急', '#dc3545'),
    ('学习', '#0d6efd'),
    ('工作', '#198754'),
    ('个人', '#6f42c1'),
    ('会议', '#fd7e14')
ON CONFLICT (name) DO NOTHING;

INSERT INTO todos (title, description, completed, priority, category, due_date)
VALUES
    ('完成 Flask 教程', '学习 Flask 框架的基础知识和路由设计', false, 'high', 'study',
     CURRENT_TIMESTAMP + INTERVAL '3 days'),
    ('编写单元测试', '覆盖所有 API 端点的测试用例', false, 'medium', 'work',
     CURRENT_TIMESTAMP + INTERVAL '5 days'),
    ('复习 PostgreSQL', '练习复杂查询和索引优化', true, 'low', 'study',
     CURRENT_TIMESTAMP - INTERVAL '1 day');

-- 建立示例标签关联
INSERT INTO todo_tags (todo_id, tag_id)
SELECT t.id, g.id FROM todos t, tags g
WHERE t.title = '完成 Flask 教程' AND g.name IN ('学习', '紧急')
ON CONFLICT DO NOTHING;

INSERT INTO todo_tags (todo_id, tag_id)
SELECT t.id, g.id FROM todos t, tags g
WHERE t.title = '编写单元测试' AND g.name = '工作'
ON CONFLICT DO NOTHING;

INSERT INTO todo_tags (todo_id, tag_id)
SELECT t.id, g.id FROM todos t, tags g
WHERE t.title = '复习 PostgreSQL' AND g.name = '学习'
ON CONFLICT DO NOTHING;

-- ════════════════════════════════════════════
-- 4. 函数与触发器：自动更新 updated_at
-- ════════════════════════════════════════════

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 仅在触发器不存在时创建
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_todos_updated_at'
    ) THEN
        CREATE TRIGGER trigger_todos_updated_at
            BEFORE UPDATE ON todos
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;
