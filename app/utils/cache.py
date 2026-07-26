"""
Redis 缓存辅助函数

采用 Cache-Aside 模式：
- 读：先查缓存，miss 则查 DB 并回填
- 写：先写 DB，再失效缓存
"""
import json
from datetime import datetime
from typing import Any, Dict, Optional

from app.extensions import get_redis


def cache_get(key: str) -> Optional[Any]:
    """从 Redis 读取缓存。"""
    r = get_redis()
    if not r:
        return None
    val = r.get(key)
    return json.loads(val) if val else None


def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    """写入 Redis 缓存。"""
    r = get_redis()
    if not r:
        return
    r.setex(key, ttl, json.dumps(value, ensure_ascii=False))


def cache_delete(key: str) -> None:
    """删除 Redis 缓存。"""
    r = get_redis()
    if r:
        r.delete(key)


def invalidate_todo_cache() -> None:
    """失效待办列表缓存（写操作后调用）。"""
    cache_delete("todos:list")


def increment_visit_stat(endpoint: str) -> None:
    """记录 API 调用热度统计。"""
    r = get_redis()
    if r:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"stats:{endpoint}:{today}"
        r.incr(key)
        r.expire(key, 86400 * 7)


def get_hot_stats() -> Dict[str, int]:
    """获取今日访问统计（使用 SCAN 避免阻塞 Redis）。"""
    r = get_redis()
    if not r:
        return {}
    today = datetime.utcnow().strftime("%Y-%m-%d")
    keys = list(r.scan_iter(f"stats:*:{today}"))
    stats: Dict[str, int] = {}
    for key in keys:
        endpoint = key.decode() if isinstance(key, bytes) else key
        endpoint = endpoint.replace("stats:", "").replace(f":{today}", "")
        stats[endpoint] = int(r.get(key) or 0)
    return stats
