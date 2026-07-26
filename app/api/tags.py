"""
标签 API 路由

Blueprint: /api/tags
"""
import logging

from flask import Blueprint, jsonify, request

from app.services import tag_service
from app.exceptions import AppException, ConflictException, ValidationException
from app.utils.cache import increment_visit_stat
from app.utils.validators import validate_color, validate_tag_name
from app.schemas.tag import TagOutSchema

logger = logging.getLogger(__name__)

tags_bp = Blueprint("tags", __name__, url_prefix="/api/tags")


def _handle_service_error(e: AppException):
    """统一异常 → HTTP 响应转换。"""
    return jsonify({"error": e.message}), e.code


@tags_bp.route("", methods=["GET"])
def get_tags():
    """获取所有标签（含待办事项计数，批量聚合避免 N+1）。"""
    increment_visit_stat("tags_list")
    result = tag_service.list_tags()
    return jsonify(result)


@tags_bp.route("", methods=["POST"])
def create_tag():
    """创建标签。"""
    increment_visit_stat("tags_create")
    data = request.get_json(silent=True)
    if not data or not data.get("name"):
        return jsonify({"error": "标签名称不能为空"}), 400

    name = data["name"].strip()
    is_valid, error = validate_tag_name(name)
    if not is_valid:
        return jsonify({"error": error}), 400

    color = data.get("color", "#6c757d")
    is_valid, error = validate_color(color)
    if not is_valid:
        return jsonify({"error": error}), 400

    try:
        tag = tag_service.create_tag(name, color)
    except ConflictException as e:
        return _handle_service_error(e)

    return jsonify(TagOutSchema.from_model(tag)), 201


@tags_bp.route("/<int:tag_id>", methods=["GET"])
def get_tag(tag_id: int):
    """查询单个标签及其关联的待办事项。"""
    increment_visit_stat("tags_detail")
    result = tag_service.get_tag_with_todos(tag_id)
    if result is None:
        return jsonify({"error": "资源未找到"}), 404
    return jsonify(result)


@tags_bp.route("/<int:tag_id>", methods=["PUT"])
def update_tag(tag_id: int):
    """更新标签名称或颜色。"""
    increment_visit_stat("tags_update")
    tag = tag_service.get_tag_by_id(tag_id)
    if tag is None:
        return jsonify({"error": "资源未找到"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    if "name" in data:
        name = data["name"].strip()
        is_valid, error = validate_tag_name(name)
        if not is_valid:
            return jsonify({"error": error}), 400
        data["name"] = name

    if "color" in data:
        is_valid, error = validate_color(data["color"])
        if not is_valid:
            return jsonify({"error": error}), 400

    try:
        tag = tag_service.update_tag(tag, data)
    except ConflictException as e:
        return _handle_service_error(e)

    return jsonify(TagOutSchema.from_model(tag))


@tags_bp.route("/<int:tag_id>", methods=["DELETE"])
def delete_tag(tag_id: int):
    """删除标签（自动解除关联）。"""
    increment_visit_stat("tags_delete")
    tag = tag_service.get_tag_by_id(tag_id)
    if tag is None:
        return jsonify({"error": "资源未找到"}), 404
    tag_service.delete_tag(tag)
    return jsonify({"message": "标签已删除"})
