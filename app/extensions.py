"""
Flask 扩展实例（延迟绑定模式）

所有扩展在此集中初始化，通过 create_app() 完成绑定。
避免循环导入，遵循 Flask 官方推荐模式。
"""
import logging
import os
import threading
from typing import Optional

import redis as redis_lib
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# ── 数据库与迁移 ──
db = SQLAlchemy()
migrate = Migrate()

# ── Redis（懒初始化 + 线程安全） ──
redis_client: Optional[redis_lib.Redis] = None
_redis_unavailable = object()  # 哨兵值
_redis_lock = threading.Lock()


def get_redis() -> Optional[redis_lib.Redis]:
    """获取 Redis 客户端（懒初始化，线程安全）。

    若 Redis 不可达则缓存失败状态，避免每次请求都重试连接。
    """
    global redis_client
    if redis_client is _redis_unavailable:
        return None
    if redis_client is None:
        with _redis_lock:
            if redis_client is None:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                try:
                    redis_client = redis_lib.from_url(
                        redis_url, socket_connect_timeout=2, decode_responses=True
                    )
                    redis_client.ping()
                    logging.getLogger(__name__).info("Redis 连接成功")
                except Exception as e:
                    logging.getLogger(__name__).warning(f"Redis 不可用，缓存功能将禁用: {e}")
                    redis_client = _redis_unavailable
                    return None
    return redis_client
