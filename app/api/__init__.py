"""
API 蓝图注册

集中管理所有蓝图，create_app() 中统一注册。
"""
from app.api.todos import todos_bp
from app.api.tags import tags_bp
from app.api.stats import stats_bp
from app.api.health import health_bp

__all__ = ["todos_bp", "tags_bp", "stats_bp", "health_bp"]
