"""
应用工厂模块

遵循 Flask 应用工厂模式，支持：
- 多环境配置切换（development / testing / production）
- 延迟扩展绑定
- SQLite 外键自动启用
"""
import logging
import os
import time

from flask import Flask
from flask_cors import CORS
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.config import config_by_name
from app.extensions import db, migrate
from app.utils.logging import setup_logging

logger = logging.getLogger(__name__)


def create_app(config_name: str = None) -> Flask:
    """创建并配置 Flask 应用。

    Args:
        config_name: 配置名（development/testing/production），
                     默认从 FLASK_ENV 环境变量读取。

    Returns:
        配置完成的 Flask 应用实例
    """
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "production")

    app = Flask(__name__)

    # ── 加载配置 ──
    config_class = config_by_name.get(config_name, config_by_name["production"])
    app.config.from_object(config_class)

    # 允许测试配置覆盖
    if os.getenv("TESTING"):
        app.config["TESTING"] = True

    # ── 初始化日志 ──
    setup_logging(app)

    # ── 初始化扩展 ──
    db.init_app(app)
    migrate.init_app(app, db)

    # ── CORS ──
    cors_origins = app.config.get("CORS_ORIGINS", "*")
    origins = cors_origins.split(",") if cors_origins != "*" else "*"
    CORS(app, origins=origins)

    # ── SQLite 外键支持 ──
    @event.listens_for(Engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        import sqlite3
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    # ── 注册蓝图 ──
    from app.api.health import health_bp
    from app.api.todos import todos_bp
    from app.api.tags import tags_bp
    from app.api.stats import stats_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(todos_bp)
    app.register_blueprint(tags_bp)
    app.register_blueprint(stats_bp)

    # ── 注册错误处理器 ──
    from app.errors.handlers import register_error_handlers
    register_error_handlers(app)

    logger.info(f"应用启动完成 (env={config_name})")
    return app


# ── 直接运行入口（开发用） ──
if __name__ == "__main__":
    app = create_app("development")
    with app.app_context():
        max_retries = 30
        for retry_count in range(max_retries):
            try:
                db.create_all()
                app.logger.info("数据库表创建成功")
                break
            except Exception as e:
                app.logger.warning(f"等待数据库连接... ({retry_count + 1}/{max_retries}) - {e}")
                time.sleep(2)
        else:
            app.logger.error("数据库连接失败，已达最大重试次数")

    app.run(debug=True, host="0.0.0.0", port=5000)
