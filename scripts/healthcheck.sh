#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
# 应用健康检查脚本
# 用于 Docker HEALTHCHECK 或外部监控系统 (Prometheus/Nagios)
# ═══════════════════════════════════════════════════════
set -eo pipefail

HOST="${1:-localhost}"
PORT="${2:-5000}"
TIMEOUT="${3:-5}"
URL="http://${HOST}:${PORT}/health"

# ── HTTP 健康检查 ──
RESPONSE=$(curl -sS --max-time "$TIMEOUT" "$URL" 2>/dev/null) || {
    echo "CRITICAL: 无法连接到 $URL"
    exit 2
}

# ── 解析响应 ──
STATUS=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")
DB_STATUS=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('database','unknown'))" 2>/dev/null || echo "unknown")

# ── 判断状态 ──
if [[ "$STATUS" == "ok" ]] && [[ "$DB_STATUS" == "ok" ]]; then
    echo "OK: 服务正常 (database=$DB_STATUS)"
    exit 0
elif [[ "$STATUS" != "ok" ]]; then
    echo "CRITICAL: 服务状态异常 (status=$STATUS)"
    exit 2
elif [[ "$DB_STATUS" != "ok" ]]; then
    echo "WARNING: 数据库连接异常 (database=$DB_STATUS)"
    exit 1
else
    echo "CRITICAL: 未知状态"
    exit 2
fi
