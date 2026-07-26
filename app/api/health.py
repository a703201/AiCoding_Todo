"""
健康检查与监控 API 路由

Blueprint: 根路径
"""
from flask import Blueprint, render_template, jsonify

from app.services import todo_service
from app.utils.cache import increment_visit_stat

health_bp = Blueprint("health", __name__)


@health_bp.route("/")
def index():
    """前端页面。"""
    increment_visit_stat("home")
    return render_template("index.html")


@health_bp.route("/health")
def health():
    """增强健康检查：数据库、Redis、磁盘、内存。"""
    health_data, http_status = todo_service.get_health_data()
    return jsonify(health_data), http_status


@health_bp.route("/metrics")
def metrics():
    """Prometheus 兼容的指标端点。"""
    metrics_text = todo_service.get_metrics_text()
    return metrics_text, 200, {"Content-Type": "text/plain; charset=utf-8"}
