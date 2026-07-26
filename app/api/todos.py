"""
待办事项 API 路由

Blueprint: /api/todos
"""
import logging

from flask import Blueprint, jsonify, request, current_app

from app.services import todo_service, tag_service
from app.exceptions import (
    AppException,
    ValidationException,
    NotFoundException,
    ConflictException,
)
from app.utils.cache import cache_get, cache_set, increment_visit_stat, invalidate_todo_cache
from app.utils.validators import validate_todo_data
from app.schemas.todo import TodoOutSchema

logger = logging.getLogger(__name__)

todos_bp = Blueprint("todos", __name__, url_prefix="/api/todos")


def _handle_service_error(e: AppException):
    """统一异常 → HTTP 响应转换。"""
    return jsonify({"error": e.message}), e.code


@todos_bp.route("", methods=["GET"])
def get_todos():
    """待办列表（搜索 + 分页 + 筛选 + 排序 + 缓存）。"""
    increment_visit_stat("list")

    # 有筛选/搜索/分页时跳过缓存
    has_filter = any(
        request.args.get(k) for k in (
            "completed", "priority", "category", "due_before",
            "search", "page", "per_page", "sort_by", "sort_order",
        )
    )

    cache_key = "todos:list"
    if not has_filter:
        cached = cache_get(cache_key)
        if cached is not None:
            logger.debug("返回缓存的待办列表")
            return jsonify(cached)

    try:
        result, pagination = todo_service.list_todos(
            completed=request.args.get("completed"),
            priority=request.args.get("priority"),
            category=request.args.get("category"),
            due_before=request.args.get("due_before"),
            search=request.args.get("search"),
            sort_by=request.args.get("sort_by", "created_at"),
            sort_order=request.args.get("sort_order", "desc"),
            page=request.args.get("page", 1, type=int),
            per_page=request.args.get("per_page", 20, type=int),
        )
    except ValidationException as e:
        return _handle_service_error(e)

    response = {"data": result, "pagination": pagination}

    if not has_filter:
        cache_set(cache_key, response, ttl=current_app.config.get("CACHE_TTL", 30))

    return jsonify(response)


@todos_bp.route("", methods=["POST"])
def create_todo():
    """创建待办事项（含 savepoint 事务）。"""
    increment_visit_stat("create")

    data = request.get_json(silent=True)
    is_valid, error = validate_todo_data(data, is_create=True)
    if not is_valid:
        return jsonify({"error": error}), 400

    try:
        todo = todo_service.create_todo(data)
    except ValidationException as e:
        return _handle_service_error(e)
    except Exception:
        logger.exception("创建待办事项异常")
        return jsonify({"error": "服务器内部错误"}), 500

    return jsonify(TodoOutSchema.from_model(todo)), 201


@todos_bp.route("/<int:todo_id>", methods=["GET"])
def get_todo(todo_id: int):
    """查询单个待办事项。"""
    increment_visit_stat("detail")
    todo = todo_service.get_todo_by_id(todo_id)
    if todo is None:
        return jsonify({"error": "资源未找到"}), 404
    return jsonify(TodoOutSchema.from_model(todo))


@todos_bp.route("/<int:todo_id>", methods=["PUT"])
def update_todo(todo_id: int):
    """更新待办事项。"""
    increment_visit_stat("update")
    todo = todo_service.get_todo_by_id(todo_id)
    if todo is None:
        return jsonify({"error": "资源未找到"}), 404

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "请求体不能为空"}), 400

    is_valid, error = validate_todo_data(data, is_create=False)
    if not is_valid:
        return jsonify({"error": error}), 400

    try:
        todo = todo_service.update_todo(todo, data)
    except ValidationException as e:
        return _handle_service_error(e)

    return jsonify(TodoOutSchema.from_model(todo))


@todos_bp.route("/<int:todo_id>", methods=["DELETE"])
def delete_todo(todo_id: int):
    """删除待办事项。"""
    increment_visit_stat("delete")
    todo = todo_service.get_todo_by_id(todo_id)
    if todo is None:
        return jsonify({"error": "资源未找到"}), 404
    todo_service.delete_todo(todo)
    return jsonify({"message": "待办事项已删除"})


@todos_bp.route("/<int:todo_id>/toggle", methods=["POST"])
def toggle_todo(todo_id: int):
    """切换完成状态。"""
    increment_visit_stat("toggle")
    todo = todo_service.get_todo_by_id(todo_id)
    if todo is None:
        return jsonify({"error": "资源未找到"}), 404
    todo = todo_service.toggle_todo(todo)
    return jsonify(TodoOutSchema.from_model(todo))


@todos_bp.route("/batch/delete-completed", methods=["POST"])
def batch_delete_completed():
    """批量删除所有已完成的待办事项。"""
    increment_visit_stat("batch_delete")
    deleted_count = todo_service.batch_delete_completed()
    return jsonify({
        "message": f"已删除 {deleted_count} 条已完成事项",
        "deleted_count": deleted_count,
    })


# ── Todo ↔ Tag 关联操作 ──


@todos_bp.route("/<int:todo_id>/tags", methods=["POST"])
def assign_tags_to_todo(todo_id: int):
    """为待办事项添加标签。"""
    increment_visit_stat("assign_tags")
    todo = todo_service.get_todo_by_id(todo_id)
    if todo is None:
        return jsonify({"error": "资源未找到"}), 404

    data = request.get_json(silent=True)
    if not data or not data.get("tag_ids"):
        return jsonify({"error": "请提供 tag_ids 数组"}), 400

    try:
        todo = tag_service.assign_tags_to_todo(todo, data["tag_ids"])
    except ValidationException as e:
        return _handle_service_error(e)

    return jsonify(TodoOutSchema.from_model(todo))


@todos_bp.route("/<int:todo_id>/tags/<int:tag_id>", methods=["DELETE"])
def remove_tag_from_todo(todo_id: int, tag_id: int):
    """移除待办事项的某个标签。"""
    increment_visit_stat("remove_tag")
    todo = todo_service.get_todo_by_id(todo_id)
    if todo is None:
        return jsonify({"error": "资源未找到"}), 404

    tag = tag_service.get_tag_by_id(tag_id)
    if tag is None:
        return jsonify({"error": "资源未找到"}), 404

    try:
        todo = tag_service.remove_tag_from_todo(todo, tag)
    except NotFoundException as e:
        return _handle_service_error(e)

    return jsonify(TodoOutSchema.from_model(todo))


@todos_bp.route("/<int:todo_id>/tags", methods=["PUT"])
def set_todo_tags(todo_id: int):
    """覆盖设置待办事项的标签。"""
    increment_visit_stat("set_tags")
    todo = todo_service.get_todo_by_id(todo_id)
    if todo is None:
        return jsonify({"error": "资源未找到"}), 404

    data = request.get_json(silent=True)
    if not data or "tag_ids" not in data:
        return jsonify({"error": "请提供 tag_ids 数组"}), 400

    try:
        todo = tag_service.set_todo_tags(todo, data["tag_ids"])
    except ValidationException as e:
        return _handle_service_error(e)

    return jsonify(TodoOutSchema.from_model(todo))
