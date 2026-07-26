"""
全局错误处理器

统一管理所有 HTTP 错误响应格式，包括自定义异常的映射。
"""
import logging

from flask import jsonify

from app.extensions import db

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """注册全局错误处理器到 Flask 应用实例。"""

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "请求参数有误"}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "资源未找到"}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"error": "请求方法不允许"}), 405

    @app.errorhandler(500)
    def internal_error(error):
        try:
            db.session.rollback()
        except Exception:
            pass
        logger.exception("服务器内部错误")
        return jsonify({"error": "服务器内部错误"}), 500

    # 注册自定义应用异常的全局处理
    from app.exceptions import AppException

    @app.errorhandler(AppException)
    def handle_app_exception(error: AppException):
        """捕获所有未在路由中显式处理的 AppException。"""
        logger.warning(f"未捕获的应用异常: [{error.code}] {error.message}")
        return jsonify({"error": error.message}), error.code
