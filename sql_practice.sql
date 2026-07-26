-- =============================================
-- SQL 查询练习：待办事项管理数据库
-- 学习目标：复杂查询、聚合、窗口函数、子查询
-- 适用数据库：PostgreSQL（部分语法 SQLite 兼容）
-- =============================================

-- ════════════════════════════════════════════
-- 1. 基础查询
-- ════════════════════════════════════════════

-- 1.1 查询所有未完成的事项，按优先级排序
SELECT * FROM todos
WHERE completed = FALSE
ORDER BY
    CASE priority
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'low' THEN 3
    END,
    created_at DESC;

-- 1.2 查询今天创建的待办事项
SELECT * FROM todos
WHERE DATE(created_at) = CURRENT_DATE;

-- 1.3 查询标题包含特定关键词的事项（模糊搜索）
SELECT id, title, priority, completed
FROM todos
WHERE title LIKE '%学习%' OR description LIKE '%学习%';

-- ════════════════════════════════════════════
-- 2. 聚合查询
-- ════════════════════════════════════════════

-- 2.1 按优先级统计数量和完成率
SELECT
    priority,
    COUNT(*) AS total,
    SUM(CASE WHEN completed = TRUE THEN 1 ELSE 0 END) AS completed_cnt,
    ROUND(
        CAST(SUM(CASE WHEN completed = TRUE THEN 1 ELSE 0 END) AS FLOAT)
        / NULLIF(COUNT(*), 0) * 100, 1
    ) AS completion_rate
FROM todos
GROUP BY priority
ORDER BY
    CASE priority
        WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3
    END;

-- 2.2 按分类统计总数量和逾期数量
SELECT
    category,
    COUNT(*) AS total,
    COUNT(CASE WHEN due_date < datetime('now') AND completed = FALSE THEN 1 END) AS overdue_cnt,
    SUM(CASE WHEN completed = TRUE THEN 1 ELSE 0 END) AS completed_cnt
FROM todos
GROUP BY category
ORDER BY total DESC;

-- 2.3 过去7天每日创建数量
SELECT
    DATE(created_at) AS day,
    COUNT(*) AS daily_cnt
FROM todos
WHERE created_at >= date('now', '-7 days')
GROUP BY DATE(created_at)
ORDER BY day;

-- ════════════════════════════════════════════
-- 3. 多表关联查询
-- ════════════════════════════════════════════

-- 3.1 查询每个标签下的待办事项数量（使用频率）
SELECT
    t.name AS tag_name,
    t.color,
    COUNT(tt.todo_id) AS usage_count
FROM tags t
LEFT JOIN todo_tags tt ON t.id = tt.tag_id
GROUP BY t.id
ORDER BY usage_count DESC;

-- 3.2 查询待办事项及其所有标签
SELECT
    td.id,
    td.title,
    GROUP_CONCAT(t.name, ', ') AS tag_list
FROM todos td
LEFT JOIN todo_tags tt ON td.id = tt.todo_id
LEFT JOIN tags t ON tt.tag_id = t.id
GROUP BY td.id
ORDER BY td.created_at DESC;

-- 3.3 找出「同时拥有两个特定标签」的待办事项
SELECT td.id, td.title
FROM todos td
JOIN todo_tags tt1 ON td.id = tt1.todo_id
JOIN tags t1 ON tt1.tag_id = t1.id AND t1.name = '紧急'
JOIN todo_tags tt2 ON td.id = tt2.todo_id
JOIN tags t2 ON tt2.tag_id = t2.id AND t2.name = '工作'
ORDER BY td.created_at DESC;

-- ════════════════════════════════════════════
-- 4. 子查询与 CTE（公共表表达式）
-- ════════════════════════════════════════════

-- 4.1 CTE：计算平均任务数并找出超出平均的分类
WITH category_counts AS (
    SELECT category, COUNT(*) AS cnt
    FROM todos
    GROUP BY category
)
SELECT *
FROM category_counts
WHERE cnt > (SELECT AVG(cnt) FROM category_counts);

-- 4.2 查找逾期且未标记为「紧急」的事项（子查询）
SELECT id, title, due_date
FROM todos
WHERE completed = FALSE
  AND due_date < datetime('now')
  AND id NOT IN (
      SELECT tt.todo_id
      FROM todo_tags tt
      JOIN tags t ON tt.tag_id = t.id
      WHERE t.name = '紧急'
  );

-- ════════════════════════════════════════════
-- 5. 事务处理示例
-- ════════════════════════════════════════════

-- 5.1 事务：批量更新并确保原子性
BEGIN;
    UPDATE todos SET priority = 'high'
    WHERE due_date < datetime('now') AND completed = FALSE;
    -- 如条件不满足可回滚：ROLLBACK;
COMMIT;

-- 5.2 使用 SAVEPOINT 的嵌套事务
BEGIN;
    INSERT INTO tags (name, color) VALUES ('临时标签', '#aaaaaa');

    SAVEPOINT sp1;
        INSERT INTO todo_tags (todo_id, tag_id)
        VALUES (1, (SELECT id FROM tags WHERE name = '临时标签'));
    -- 如果出错：ROLLBACK TO sp1; 不影响外层事务
    RELEASE SAVEPOINT sp1;

COMMIT;

-- ════════════════════════════════════════════
-- 6. 索引查询性能分析
-- ════════════════════════════════════════════

-- 6.1 查看查询计划（EXPLAIN）
-- EXPLAIN SELECT * FROM todos WHERE completed = FALSE AND priority = 'high';
-- 预期输出：应使用 ix_todos_completed_priority 复合索引

-- 6.2 对比有无索引的查询计划
-- EXPLAIN QUERY PLAN SELECT * FROM todos WHERE category = 'work' AND priority = 'high';
-- 预期输出：USING INDEX ix_todos_category_priority

-- ════════════════════════════════════════════
-- 7. 窗口函数（PostgreSQL）
-- ════════════════════════════════════════════

-- 7.1 按优先级分组，组内按创建时间排序编号
SELECT
    id, title, priority, created_at,
    ROW_NUMBER() OVER (PARTITION BY priority ORDER BY created_at DESC) AS row_num
FROM todos
ORDER BY priority, row_num;

-- 7.2 计算累计创建数量（滚动总计）
SELECT
    DATE(created_at) AS day,
    COUNT(*) AS daily_cnt,
    SUM(COUNT(*)) OVER (ORDER BY DATE(created_at)) AS cumulative_cnt
FROM todos
GROUP BY DATE(created_at)
ORDER BY day;
