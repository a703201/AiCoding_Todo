"""
Gunicorn 生产配置
用途：gunicorn -c gunicorn.conf.py "app:create_app()"
"""
import multiprocessing
import os

# ── 绑定地址 ──
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

# ── 工作进程（推荐: CPU核心数 * 2 + 1） ──
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))

# ── 工作模式（默认 sync，适合 CPU 密集型） ──
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "sync")

# ── 线程数（sync 模式下每个 worker 的线程数） ──
threads = int(os.getenv("GUNICORN_THREADS", 2))

# ── 超时配置 ──
timeout = int(os.getenv("GUNICORN_TIMEOUT", 30))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", 30))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", 2))

# ── 连接限制 ──
worker_connections = int(os.getenv("GUNICORN_WORKER_CONNECTIONS", 1000))
backlog = int(os.getenv("GUNICORN_BACKLOG", 2048))

# ── 预加载应用（减少内存占用，但需注意数据库连接池在 fork 后的共享问题） ──
# 如果使用 PostgreSQL 连接池，建议设为 false
preload_app = os.getenv("GUNICORN_PRELOAD_APP", "false").lower() == "true"

# ── 最大请求数（防止内存泄漏，处理 N 个请求后重启 worker） ──
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", 10000))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", 1000))

# ── 日志配置 ──
log_dir = os.getenv("LOG_DIR", "/app/logs")
os.makedirs(log_dir, exist_ok=True)

accesslog = os.path.join(log_dir, "gunicorn-access.log")
errorlog = os.path.join(log_dir, "gunicorn-error.log")
loglevel = os.getenv("LOG_LEVEL", "info").lower()

# 访问日志格式（包含响应时间）
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s '
    '"%(f)s" "%(a)s" %(L)s'
)

# ── 进程命名 ──
proc_name = "todo-app"

# ── 安全：降权运行 ──
user = os.getenv("APP_USER", None)
group = os.getenv("APP_GROUP", None)

# ── 优雅重启 ──
pidfile = os.getenv("GUNICORN_PIDFILE", "/tmp/gunicorn.pid")

# ── 请求头配置 ──
forwarded_allow_ips = "*"
proxy_protocol = False
