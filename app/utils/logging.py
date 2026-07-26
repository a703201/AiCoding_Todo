"""
日志配置模块

- 开发环境：控制台人类可读格式
- 生产环境：控制台 WARNING+ 级别 + JSON 文件日志按天轮转，保留 30 天
"""
import logging
import os
from logging.handlers import TimedRotatingFileHandler

from pythonjsonlogger import jsonlogger


def setup_logging(app):
    """配置应用日志。"""
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    log_dir = os.getenv("LOG_DIR", "/app/logs")
    os.makedirs(log_dir, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    flask_env = os.getenv("FLASK_ENV", "production")

    if flask_env == "development":
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_fmt)
        root_logger.addHandler(console_handler)
    else:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(message)s")
        console_handler.setFormatter(console_fmt)
        root_logger.addHandler(console_handler)

        file_handler = TimedRotatingFileHandler(
            filename=os.path.join(log_dir, "app.log"),
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        json_fmt = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        file_handler.setFormatter(json_fmt)
        root_logger.addHandler(file_handler)

    app.logger.info(f"日志系统初始化完成 (level={log_level_name}, env={flask_env})")
