#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
# 测试运行脚本
# 支持: 单元测试 / 覆盖率报告 / 并行执行
# ═══════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ──────────────────────────────────────────
# 参数
# ──────────────────────────────────────────
COVERAGE=false
PARALLEL=false
WATCH=false
VERBOSE=false
SPECIFIC_TEST=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage|-c) COVERAGE=true; shift ;;
        --parallel|-p) PARALLEL=true; shift ;;
        --watch|-w)    WATCH=true; shift ;;
        --verbose|-v)  VERBOSE=true; shift ;;
        -k)            SPECIFIC_TEST="-k $2"; shift 2 ;;
        *)             SPECIFIC_TEST="$SPECIFIC_TEST $1"; shift ;;
    esac
done

# ──────────────────────────────────────────
# 构建 pytest 参数
# ──────────────────────────────────────────
PYTEST_ARGS="-v"

if $VERBOSE; then
    PYTEST_ARGS="$PYTEST_ARGS --tb=long"
else
    PYTEST_ARGS="$PYTEST_ARGS --tb=short"
fi

if $COVERAGE; then
    PYTEST_ARGS="$PYTEST_ARGS --cov=. --cov-report=term-missing --cov-report=html --cov-report=xml"
    if [[ -f ".coveragerc" ]]; then
        PYTEST_ARGS="$PYTEST_ARGS --cov-config=.coveragerc"
    fi
fi

if $PARALLEL; then
    PYTEST_ARGS="$PYTEST_ARGS -n auto"
fi

if [[ -n "$SPECIFIC_TEST" ]]; then
    PYTEST_ARGS="$PYTEST_ARGS $SPECIFIC_TEST"
fi

# ──────────────────────────────────────────
# 安装依赖检查
# ──────────────────────────────────────────
if ! python3 -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}pytest 未安装，正在安装...${NC}"
    pip install pytest pytest-cov
fi

# ──────────────────────────────────────────
# 运行
# ──────────────────────────────────────────
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  运行测试${NC}"

if $COVERAGE; then echo "  覆盖率: 启用"; fi
if $PARALLEL; then echo "  并行执行: 启用"; fi

echo -e "${GREEN}============================================${NC}"
echo ""

START_TIME=$(date +%s)

if $WATCH; then
    # 需要 pytest-watch
    pip install pytest-watch 2>/dev/null || true
    ptw tests/ -- $PYTEST_ARGS
else
    python3 -m pytest tests/ $PYTEST_ARGS
fi

EXIT_CODE=$?
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  耗时: ${DURATION}s${NC}"

if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}  结果: 全部通过 ✓${NC}"
else
    echo -e "${RED}  结果: 测试失败 ✗${NC}"
fi

echo -e "${GREEN}============================================${NC}"

if $COVERAGE && [[ $EXIT_CODE -eq 0 ]]; then
    echo ""
    echo -e "覆盖率报告: ${GREEN}htmlcov/index.html${NC}"
fi

exit $EXIT_CODE
