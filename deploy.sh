#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
# 待办事项应用 - 自动化部署脚本
# 用法: ./deploy.sh [production|staging]
# ═══════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ──────────────────────────────────────────
# 颜色输出
# ──────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*"; }
log_step()    { echo -e "${BLUE}==>${NC} $*"; }

# ──────────────────────────────────────────
# 参数解析
# ──────────────────────────────────────────
ENVIRONMENT="${1:-production}"
COMPOSE_FILE="docker-compose.yml"

if [[ "$ENVIRONMENT" == "staging" ]]; then
    log_warn "使用 staging 环境配置"
    export COMPOSE_FILE="docker-compose.yml"
elif [[ "$ENVIRONMENT" != "production" ]]; then
    log_error "未知环境: $ENVIRONMENT (可选: production, staging)"
    exit 1
fi

# ──────────────────────────────────────────
# 前置检查
# ──────────────────────────────────────────

log_step "检查依赖..."

command -v docker >/dev/null 2>&1 || { log_error "Docker 未安装"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { log_error "Docker Compose 未安装"; exit 1; }

# ──────────────────────────────────────────
# 环境变量检查
# ──────────────────────────────────────────

log_step "检查环境变量..."

if [[ ! -f ".env" ]]; then
    if [[ -f "env.example" ]]; then
        log_warn ".env 文件不存在，从 env.example 创建..."
        cp env.example .env
        log_warn "请编辑 .env 文件设置正确的值！"
        if [[ "$ENVIRONMENT" == "production" ]]; then
            log_error "生产环境必须有正确的 .env 配置"
            exit 1
        fi
    else
        log_error "env.example 文件不存在"
        exit 1
    fi
fi

# 加载 .env
set -a
source .env
set +a

# 生产环境安全检查
if [[ "$ENVIRONMENT" == "production" ]]; then
    if [[ "${SECRET_KEY:-change-me-in-production}" == "change-me-in-production" ]] || \
       [[ "${SECRET_KEY:-dev-secret-key}" == "dev-secret-key" ]]; then
        log_error "生产环境必须设置安全的 SECRET_KEY"
        log_error "请编辑 .env 文件：SECRET_KEY=<随机字符串>"
        echo ""
        echo "生成随机密钥命令："
        echo "  python -c \"import secrets; print(secrets.token_urlsafe(64))\""
        exit 1
    fi

    if [[ "${DATABASE_URL:-}" == *"todo_password"* ]] || [[ "${DATABASE_URL:-}" == *"todo_user"* ]]; then
        log_warn "建议修改 PostgreSQL 默认密码"
    fi

    if [[ "${FLASK_ENV:-production}" == "development" ]]; then
        log_error "生产环境 FLASK_ENV 必须为 'production'"
        exit 1
    fi
fi

# ──────────────────────────────────────────
# 测试
# ──────────────────────────────────────────

log_step "运行测试..."

if command -v python3 >/dev/null 2>&1; then
    python3 -m pytest tests/ -v --tb=short 2>&1 | tail -5 || {
        log_error "测试未通过，部署中止"
        exit 1
    }
    log_info "测试通过 ✓"
else
    log_warn "Python3 不可用，跳过测试"
fi

# ──────────────────────────────────────────
# 构建并部署
# ──────────────────────────────────────────

log_step "停止旧服务..."

docker-compose down --remove-orphans 2>/dev/null || true

log_step "构建镜像..."

docker-compose build --no-cache

log_step "启动服务..."

docker-compose up -d

log_step "等待服务就绪..."

MAX_RETRIES=30
RETRY_COUNT=0
while [[ $RETRY_COUNT -lt $MAX_RETRIES ]]; do
    if curl -sf http://localhost:5000/health >/dev/null 2>&1; then
        log_info "应用就绪 ✓"
        break
    fi
    sleep 2
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
done

if [[ $RETRY_COUNT -ge $MAX_RETRIES ]]; then
    log_error "应用启动超时"
    echo ""
    log_warn "查看日志："
    echo "  docker-compose logs todo-app"
    exit 1
fi

# ──────────────────────────────────────────
# 部署后检查
# ──────────────────────────────────────────

log_step "部署后检查..."

# 健康检查
HEALTH_RESP=$(curl -s http://localhost:5000/health)
log_info "健康状态: $(echo $HEALTH_RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")"
log_info "数据库状态: $(echo $HEALTH_RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['database'])")"

# 服务状态
log_step "服务状态:"
docker-compose ps

# ──────────────────────────────────────────
# 迁移（可选）
# ──────────────────────────────────────────

read -p "是否执行数据库迁移？[y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_step "执行数据库迁移..."
    docker-compose exec todo-app flask db upgrade || log_error "迁移失败"
    log_info "迁移完成 ✓"
fi

# ──────────────────────────────────────────
# 完成
# ──────────────────────────────────────────

log_info "部署完成！"
echo ""
echo "访问地址："
if [[ "$ENVIRONMENT" == "production" ]]; then
    echo "  http://localhost:80  (通过 Nginx)"
else
    echo "  http://localhost:5000"
fi
echo ""
echo "健康检查："
echo "  curl http://localhost:5000/health"
echo ""
echo "查看日志："
echo "  docker-compose logs -f"
echo ""
echo "停止服务："
echo "  docker-compose down"
