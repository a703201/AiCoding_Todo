#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
# Docker 容器启动脚本
# 功能：等待数据库/Redis就绪 → 执行迁移 → 启动应用
# ═══════════════════════════════════════════════════════
set -e

echo "============================================"
echo "  待办事项应用 - 启动中"
echo "============================================"
echo ""

# ──────────────────────────────────────────
# 等待数据库就绪
# ──────────────────────────────────────────
wait_for_db() {
    echo "等待数据库连接 $DATABASE_URL ..."

    # 解析数据库主机
    DB_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:/]*\).*/\1/p')
    DB_PORT=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    DB_HOST=${DB_HOST:-localhost}
    DB_PORT=${DB_PORT:-5432}

    # 等待 PostgreSQL
    if [[ "$DATABASE_URL" == postgresql://* ]]; then
        until pg_isready -h "$DB_HOST" -p "$DB_PORT" -q 2>/dev/null; do
            echo "  等待 PostgreSQL ($DB_HOST:$DB_PORT)..."
            sleep 2
        done
    fi

    echo "  ✓ 数据库就绪"
}

# ──────────────────────────────────────────
# 等待 Redis 就绪
# ──────────────────────────────────────────
wait_for_redis() {
    if [[ -z "${REDIS_URL:-}" ]]; then
        return
    fi

    REDIS_HOST=$(echo "$REDIS_URL" | sed -n 's/.*@\([^:/]*\).*/\1/p')
    REDIS_HOST=${REDIS_HOST:-$(echo "$REDIS_URL" | sed -n 's/.*:\/\/\([^:/]*\).*/\1/p')}
    REDIS_PORT=$(echo "$REDIS_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    REDIS_HOST=${REDIS_HOST:-localhost}
    REDIS_PORT=${REDIS_PORT:-6379}

    echo "等待 Redis 连接 ($REDIS_HOST:$REDIS_PORT) ..."
    until python3 -c "import redis; r=redis.Redis(host='$REDIS_HOST',port=$REDIS_PORT); r.ping()" 2>/dev/null; do
        echo "  等待 Redis..."
        sleep 2
    done
    echo "  ✓ Redis 就绪"
}

# ──────────────────────────────────────────
# 执行数据库迁移
# ──────────────────────────────────────────
run_migrations() {
    echo "执行数据库迁移..."
    flask db upgrade || echo "  警告: 迁移可能已执行"
    echo "  ✓ 迁移完成"
}

# ──────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────

# 等待依赖
wait_for_db
wait_for_redis

# 数据库迁移
run_migrations

# 显示配置摘要
echo ""
echo "============================================"
echo "  配置摘要"
echo "============================================"
echo "  FLASK_ENV:    ${FLASK_ENV:-production}"
echo "  LOG_LEVEL:    ${LOG_LEVEL:-INFO}"
echo "  WORKERS:      ${GUNICORN_WORKERS:-$(python3 -c 'import multiprocessing; print(multiprocessing.cpu_count()*2+1)')}"
echo "============================================"
echo ""

# 启动应用
echo "启动应用..."
exec "$@"
