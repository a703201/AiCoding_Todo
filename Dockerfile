FROM python:3.9-slim

WORKDIR /app

# Python 环境优化
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    FLASK_ENV=production \
    LOG_LEVEL=INFO \
    LOG_DIR=/app/logs

# 系统依赖（含 curl 供健康检查使用）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建日志和备份目录
RUN mkdir -p /app/logs /app/backups

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码和脚本
COPY . .

# 赋予脚本执行权限
RUN chmod +x startup.sh deploy.sh run_tests.sh scripts/*.sh

# 创建非 root 用户运行应用
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

USER app

EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -sf http://localhost:5000/health || exit 1

# 使用 startup.sh 启动（等待依赖 → 迁移 → Gunicorn）
ENTRYPOINT ["./startup.sh"]
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:create_app()"]
