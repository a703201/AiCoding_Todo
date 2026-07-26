# ════════════════════════════════════════════
# 待办事项应用 Makefile
# 用法: make <target>
# ════════════════════════════════════════════

.PHONY: help install test coverage test-all lint clean build run deploy stop logs migrate upgrade downgrade health shell db-shell redis-cli backup restore

# 默认目标
help:
	@echo "待办事项应用 - 可用命令:"
	@echo ""
	@echo "  开发:"
	@echo "    make install      安装依赖"
	@echo "    make run          启动开发服务器"
	@echo "    make test         运行测试"
	@echo "    make coverage     测试覆盖率报告"
	@echo "    make lint         代码检查"
	@echo "    make clean        清理临时文件"
	@echo ""
	@echo "  构建与部署:"
	@echo "    make build        构建 Docker 镜像"
	@echo "    make deploy       部署生产环境"
	@echo "    make stop         停止所有服务"
	@echo "    make logs         查看日志"
	@echo "    make restart      重启服务"
	@echo ""
	@echo "  数据库:"
	@echo "    make migrate      执行数据库迁移"
	@echo "    make upgrade      (别名) 执行迁移"
	@echo "    make downgrade    回滚上一次迁移"
	@echo "    make db-shell     数据库命令行"
	@echo "    make backup       备份数据库"
	@echo "    make restore      恢复数据库"
	@echo ""
	@echo "  运维:"
	@echo "    make health       健康检查"
	@echo "    make shell        进入应用容器"
	@echo "    make redis-cli    进入 Redis 命令行"
	@echo "    make stats        查看资源使用"

# ──────────────────────────────────────────
# 开发
# ──────────────────────────────────────────

install:
	pip install -r requirements.txt

run:
	python app.py

test:
	python -m pytest tests/ -v --tb=short

coverage:
	python -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing
	@echo ""
	@echo "Coverage report: htmlcov/index.html"

test-all:
	python -m pytest tests/ -v --tb=long --cov=. --cov-report=html --cov-report=xml

lint:
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=migrations,__pycache__,.tutorial
	flake8 . --count --exit-zero --max-complexity=10 --statistics --exclude=migrations,__pycache__,.tutorial

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml .pytest_cache/ 2>/dev/null || true

# ──────────────────────────────────────────
# 构建与部署
# ──────────────────────────────────────────

build:
	docker-compose build --no-cache

deploy:
	bash deploy.sh production

stop:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f --tail=100

# ──────────────────────────────────────────
# 数据库
# ──────────────────────────────────────────

migrate: upgrade
upgrade:
	docker-compose exec todo-app flask db upgrade

downgrade:
	docker-compose exec todo-app flask db downgrade

db-shell:
	docker-compose exec db psql -U todo_user -d todo_db

backup:
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	mkdir -p backups; \
	docker-compose exec -T db pg_dump -U todo_user -d todo_db > "backups/backup_$$timestamp.sql"; \
	echo "已备份到: backups/backup_$$timestamp.sql"

restore:
	@read -p "输入备份文件路径: " backup_file; \
	docker-compose exec -T db psql -U todo_user -d todo_db < "$$backup_file"; \
	echo "已恢复: $$backup_file"

# ──────────────────────────────────────────
# 运维
# ──────────────────────────────────────────

health:
	@curl -s http://localhost:5000/health | python -m json.tool || echo "服务不可用"
	@echo ""
	@echo "Docker 状态:"
	@docker-compose ps

shell:
	docker-compose exec todo-app /bin/bash

redis-cli:
	docker-compose exec redis redis-cli

stats:
	@echo "容器资源使用:"
	@docker stats --no-stream $$(docker-compose ps -q) 2>/dev/null || echo "没有运行中的容器"
