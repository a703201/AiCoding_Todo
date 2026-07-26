#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
# 数据库备份脚本
# 用法: ./scripts/backup.sh [--cron]
# ═══════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

BACKUP_DIR="${BACKUP_DIR:-backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="todo_backup_${TIMESTAMP}.sql"
COMPRESSED="todo_backup_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "开始备份: $TIMESTAMP"

# 备份
docker-compose exec -T db pg_dump -U todo_user -d todo_db | gzip > "$BACKUP_DIR/$COMPRESSED" 2>/dev/null || {
    echo "备份失败！请确认 Docker 服务正在运行。"
    exit 1
}

# 检查备份文件大小
FILE_SIZE=$(stat -c%s "$BACKUP_DIR/$COMPRESSED" 2>/dev/null || stat -f%z "$BACKUP_DIR/$COMPRESSED" 2>/dev/null || echo 0)
if [[ "$FILE_SIZE" -lt 100 ]]; then
    echo "警告: 备份文件过小 (${FILE_SIZE} bytes)，可能不完整"
fi

# 清理旧备份
echo "清理 ${RETENTION_DAYS} 天前的备份..."
find "$BACKUP_DIR" -name "todo_backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true

# 摘要
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "todo_backup_*.sql.gz" | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

echo ""
echo "============================================"
echo "  备份完成"
echo "============================================"
echo "  文件: $BACKUP_DIR/$COMPRESSED"
echo "  大小: $(du -h "$BACKUP_DIR/$COMPRESSED" | cut -f1)"
echo "  保留备份数: $BACKUP_COUNT"
echo "  总占用空间: $TOTAL_SIZE"
echo "============================================"
