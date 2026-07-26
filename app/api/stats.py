"""
统计与仪表盘 API 路由

Blueprint: /api/stats
"""
from flask import Blueprint, jsonify

from app.services import todo_service
from app.utils.cache import increment_visit_stat

stats_bp = Blueprint("stats", __name__, url_prefix="/api/stats")


@stats_bp.route("", methods=["GET"])
def api_stats():
    """返回统计信息：热点、聚合统计。"""
    stats = todo_service.get_stats()
    return jsonify(stats)


@stats_bp.route("/dashboard", methods=["GET"])
def dashboard_stats():
    """仪表盘：多维聚合统计。"""
    increment_visit_stat("dashboard")
    result = todo_service.get_dashboard_stats()
    return jsonify(result)
