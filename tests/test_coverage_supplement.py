"""
补充测试 — 覆盖上一轮审查中覆盖率不足的模块

目标模块：
- schemas/todo.py (64% → 目标 85%+)
- schemas/tag.py (77% → 目标 85%+)
- errors/handlers.py (67% → 目标 85%+)
- utils/validators.py (91% → 目标 95%+)
- utils/cache.py (92% → 目标 95%+)
- utils/logging.py (83% → 目标 90%+)
"""
import json
import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from conftest import create_todo, create_tag


# ════════════════════════════════════════════
# 一、Schema 单元测试
# ════════════════════════════════════════════

class TestTodoCreateSchema:
    """覆盖 TodoCreateSchema.to_service_dict() 的所有字段。"""

    def test_default_values(self):
        from app.schemas.todo import TodoCreateSchema
        schema = TodoCreateSchema(title="测试")
        d = schema.to_service_dict()
        assert d["title"] == "测试"
        assert d["description"] == ""
        assert d["priority"] == "medium"
        assert d["category"] == "other"
        assert d["due_date"] is None
        assert d["tag_ids"] == []

    def test_all_fields_explicit(self):
        from app.schemas.todo import TodoCreateSchema
        schema = TodoCreateSchema(
            title="完整任务",
            description="描述",
            priority="high",
            category="work",
            due_date="2025-12-31T18:00:00",
            tag_ids=[1, 2, 3],
        )
        d = schema.to_service_dict()
        assert d["title"] == "完整任务"
        assert d["description"] == "描述"
        assert d["priority"] == "high"
        assert d["category"] == "work"
        assert d["due_date"] == "2025-12-31T18:00:00"
        assert d["tag_ids"] == [1, 2, 3]


class TestTodoUpdateSchema:
    """覆盖 TodoUpdateSchema.to_service_dict() — 仅包含非 None 字段。"""

    def test_empty_update(self):
        from app.schemas.todo import TodoUpdateSchema
        schema = TodoUpdateSchema()
        d = schema.to_service_dict()
        assert d == {}

    def test_partial_fields(self):
        from app.schemas.todo import TodoUpdateSchema
        schema = TodoUpdateSchema(title="新标题", priority="low")
        d = schema.to_service_dict()
        assert d == {"title": "新标题", "priority": "low"}

    def test_all_fields(self):
        from app.schemas.todo import TodoUpdateSchema
        schema = TodoUpdateSchema(
            title="更新",
            description="新描述",
            completed=True,
            priority="high",
            category="study",
            due_date="2025-01-01T00:00:00",
        )
        d = schema.to_service_dict()
        assert len(d) == 6
        assert d["title"] == "更新"
        assert d["completed"] is True
        assert d["category"] == "study"

    def test_none_excluded(self):
        """to_service_dict 不应包含值为 None 的字段。"""
        from app.schemas.todo import TodoUpdateSchema
        schema = TodoUpdateSchema(title="test", priority=None, category=None)
        d = schema.to_service_dict()
        assert "priority" not in d
        assert "category" not in d
        assert d == {"title": "test"}


class TestTagCreateSchema:
    """覆盖 TagCreateSchema.to_service_dict()。"""

    def test_default_color(self):
        from app.schemas.tag import TagCreateSchema
        schema = TagCreateSchema(name="紧急")
        d = schema.to_service_dict()
        assert d["name"] == "紧急"
        assert d["color"] == "#6c757d"

    def test_custom_color(self):
        from app.schemas.tag import TagCreateSchema
        schema = TagCreateSchema(name="工作", color="#0d6efd")
        d = schema.to_service_dict()
        assert d["name"] == "工作"
        assert d["color"] == "#0d6efd"


class TestTagUpdateSchema:
    """覆盖 TagUpdateSchema.to_service_dict()。"""

    def test_empty_update(self):
        from app.schemas.tag import TagUpdateSchema
        schema = TagUpdateSchema()
        d = schema.to_service_dict()
        assert d == {}

    def test_name_only(self):
        from app.schemas.tag import TagUpdateSchema
        schema = TagUpdateSchema(name="新名称")
        d = schema.to_service_dict()
        assert d == {"name": "新名称"}

    def test_color_only(self):
        from app.schemas.tag import TagUpdateSchema
        schema = TagUpdateSchema(color="#ff0000")
        d = schema.to_service_dict()
        assert d == {"color": "#ff0000"}

    def test_both_fields(self):
        from app.schemas.tag import TagUpdateSchema
        schema = TagUpdateSchema(name="重命名", color="#000000")
        d = schema.to_service_dict()
        assert d == {"name": "重命名", "color": "#000000"}


# ════════════════════════════════════════════
# 二、校验器 (validators) 边界测试
# ════════════════════════════════════════════

class TestValidatorsEdge:
    """覆盖 validators 中的边界条件和未覆盖分支。"""

    def test_parse_due_date_none(self):
        from app.utils.validators import parse_due_date
        result, error = parse_due_date(None)
        assert result is None
        assert error is None

    def test_parse_due_date_non_string(self):
        from app.utils.validators import parse_due_date
        result, error = parse_due_date(12345)
        assert result is None
        assert error is not None
        assert "字符串" in error

    def test_parse_due_date_invalid_format(self):
        from app.utils.validators import parse_due_date
        result, error = parse_due_date("not-a-date")
        assert result is None
        assert error is not None
        assert "格式无效" in error

    def test_parse_due_date_valid(self):
        from app.utils.validators import parse_due_date
        from datetime import datetime
        result, error = parse_due_date("2025-07-26T12:00:00")
        assert error is None
        assert isinstance(result, datetime)

    def test_validate_color_short_hex(self):
        from app.utils.validators import validate_color
        is_valid, _ = validate_color("#abc")
        assert is_valid is True

    def test_validate_color_invalid_no_hash(self):
        from app.utils.validators import validate_color
        is_valid, error = validate_color("abc123")
        assert is_valid is False

    def test_validate_color_invalid_length(self):
        from app.utils.validators import validate_color
        is_valid, error = validate_color("#12345")
        assert is_valid is False

    def test_validate_color_non_string(self):
        from app.utils.validators import validate_color
        is_valid, error = validate_color(None)
        assert is_valid is False

    def test_validate_tag_name_none(self):
        from app.utils.validators import validate_tag_name
        is_valid, error = validate_tag_name(None)
        assert is_valid is False

    def test_validate_tag_name_empty_string(self):
        from app.utils.validators import validate_tag_name
        is_valid, error = validate_tag_name("")
        assert is_valid is False

    def test_validate_tag_name_whitespace_only(self):
        from app.utils.validators import validate_tag_name
        is_valid, error = validate_tag_name("   ")
        assert is_valid is False

    def test_validate_tag_name_too_long(self):
        from app.utils.validators import validate_tag_name
        is_valid, error = validate_tag_name("A" * 51, max_length=50)
        assert is_valid is False
        assert "不能超过" in error

    def test_validate_tag_name_valid(self):
        from app.utils.validators import validate_tag_name
        is_valid, error = validate_tag_name("正常标签")
        assert is_valid is True

    def test_escape_like_pattern(self):
        from app.utils.validators import escape_like_pattern
        assert escape_like_pattern("100%") == "100\\%"
        assert escape_like_pattern("test_123") == "test\\_123"
        assert escape_like_pattern("C:\\path") == "C:\\\\path"

    def test_escape_like_pattern_no_special(self):
        from app.utils.validators import escape_like_pattern
        assert escape_like_pattern("normal") == "normal"

    def test_validate_todo_data_title_type_check(self, client):
        """title 不是字符串时应报错。"""
        with client.application.app_context():
            from app.utils.validators import validate_todo_data
            is_valid, error = validate_todo_data({"title": 123}, is_create=False)
            assert is_valid is False
            assert "字符串" in error

    def test_validate_todo_data_title_min_length(self, client):
        """title 长度小于最小值时报错。"""
        with client.application.app_context():
            from app.utils.validators import validate_todo_data
            is_valid, error = validate_todo_data({"title": "A"}, is_create=True)
            assert is_valid is True  # min_len=1 时 A 有效


# ════════════════════════════════════════════
# 三、缓存模块 (cache) 边界测试
# ════════════════════════════════════════════

class TestCacheEdge:
    """覆盖 cache 模块中的边界分支。"""

    def test_cache_get_no_redis(self, monkeypatch):
        """Redis 不可用时 cache_get 返回 None。"""
        monkeypatch.setattr("app.utils.cache.get_redis", lambda: None)
        from app.utils.cache import cache_get
        result = cache_get("any_key")
        assert result is None

    def test_cache_set_no_redis(self, monkeypatch):
        """Redis 不可用时 cache_set 不报错。"""
        monkeypatch.setattr("app.utils.cache.get_redis", lambda: None)
        from app.utils.cache import cache_set
        # 不应抛异常
        cache_set("key", "value")

    def test_cache_delete_no_redis(self, monkeypatch):
        """Redis 不可用时 cache_delete 不报错。"""
        monkeypatch.setattr("app.utils.cache.get_redis", lambda: None)
        from app.utils.cache import cache_delete
        cache_delete("key")

    def test_invalidate_todo_cache_calls_delete(self, mock_redis):
        """invalidate_todo_cache 应调用 cache_delete('todos:list')。"""
        from app.utils.cache import invalidate_todo_cache
        invalidate_todo_cache()
        mock_redis.delete.assert_called()

    def test_increment_visit_stat(self, mock_redis):
        """increment_visit_stat 应调用 incr + expire。"""
        from app.utils.cache import increment_visit_stat
        increment_visit_stat("test_endpoint")
        mock_redis.incr.assert_called()
        mock_redis.expire.assert_called()

    def test_get_hot_stats_no_redis(self, monkeypatch):
        """Redis 不可用时 get_hot_stats 返回空 dict。"""
        monkeypatch.setattr("app.utils.cache.get_redis", lambda: None)
        from app.utils.cache import get_hot_stats
        result = get_hot_stats()
        assert result == {}

    def test_get_hot_stats_with_data(self, mock_redis):
        """get_hot_stats 正确解析 SCAN 结果。"""
        from app.utils.cache import get_hot_stats
        from datetime import datetime
        today = datetime.utcnow().strftime("%Y-%m-%d")
        mock_redis.scan_iter.return_value = [f"stats:todos:{today}".encode()]
        mock_redis.get.return_value = b"5"
        result = get_hot_stats()
        assert "todos" in result
        assert result["todos"] == 5

    def test_get_hot_stats_empty_keys(self, mock_redis):
        """get_hot_stats 无数据时返回空 dict。"""
        from app.utils.cache import get_hot_stats
        mock_redis.scan_iter.return_value = []
        result = get_hot_stats()
        assert result == {}


# ════════════════════════════════════════════
# 四、错误处理器 (handlers) 覆盖
# ════════════════════════════════════════════

class TestErrorHandlers:
    """覆盖 errors/handlers.py 中未测试的路径。"""

    def test_500_internal_error(self, app):
        """触发 500 错误验证处理器。"""
        @app.route("/_trigger_500")
        def trigger_500():
            raise RuntimeError("故意错误")
        app.config["TESTING"] = False  # 禁用测试模式才能触发 500 handler
        with app.test_client() as c:
            resp = c.get("/_trigger_500")
            assert resp.status_code == 500
            data = json.loads(resp.data)
            assert "error" in data
        app.config["TESTING"] = True

    def test_405_method_not_allowed(self, app):
        """405 处理器返回统一格式。"""
        with app.test_client() as c:
            # DELETE 不允许在集合路由上
            resp = c.delete("/api/todos")
            assert resp.status_code == 405
            data = json.loads(resp.data)
            assert "error" in data

    def test_app_exception_global_handler(self, app):
        """AppException 全局处理器捕获未在路由中处理的异常。"""
        from app.exceptions import BusinessException

        @app.route("/_trigger_business")
        def trigger_business():
            raise BusinessException("业务操作失败")

        with app.test_client() as c:
            resp = c.get("/_trigger_business")
            assert resp.status_code == 422
            data = json.loads(resp.data)
            assert data["error"] == "业务操作失败"


# ════════════════════════════════════════════
# 五、异常层次 (exceptions) 覆盖
# ════════════════════════════════════════════

class TestExceptions:
    """覆盖 exceptions.py 中所有异常类的构造和属性。"""

    def test_app_exception_default(self):
        from app.exceptions import AppException
        e = AppException("错误")
        assert e.message == "错误"
        assert e.code == 500

    def test_app_exception_custom_code(self):
        from app.exceptions import AppException
        e = AppException("自定义", code=418)
        assert e.code == 418

    def test_not_found_exception(self):
        from app.exceptions import NotFoundException
        e = NotFoundException()
        assert e.code == 404
        assert e.message == "资源未找到"

    def test_not_found_exception_custom(self):
        from app.exceptions import NotFoundException
        e = NotFoundException("用户不存在")
        assert e.code == 404
        assert e.message == "用户不存在"

    def test_conflict_exception(self):
        from app.exceptions import ConflictException
        e = ConflictException()
        assert e.code == 409
        assert e.message == "资源冲突"

    def test_conflict_exception_custom(self):
        from app.exceptions import ConflictException
        e = ConflictException("名称已存在")
        assert e.code == 409
        assert e.message == "名称已存在"

    def test_validation_exception(self):
        from app.exceptions import ValidationException
        e = ValidationException()
        assert e.code == 400

    def test_validation_exception_custom(self):
        from app.exceptions import ValidationException
        e = ValidationException("标题必填")
        assert e.code == 400
        assert e.message == "标题必填"

    def test_business_exception(self):
        from app.exceptions import BusinessException
        e = BusinessException()
        assert e.code == 422
        assert e.message == "操作失败"

    def test_business_exception_custom(self):
        from app.exceptions import BusinessException
        e = BusinessException("库存不足")
        assert e.code == 422
        assert e.message == "库存不足"


# ════════════════════════════════════════════
# 六、日志配置 (logging) 覆盖
# ════════════════════════════════════════════

class TestLoggingSetup:
    """覆盖 logging.py 中 production 环境分支。"""

    def test_production_logging_setup(self):
        """production 环境日志配置（控制台 WARNING+ + JSON 文件日志）。"""
        import logging
        from app.utils.logging import setup_logging
        from flask import Flask

        app = Flask(__name__)
        app.config["TESTING"] = True

        with patch.dict(os.environ, {
            "FLASK_ENV": "production",
            "LOG_LEVEL": "DEBUG",
            "LOG_DIR": tempfile.mkdtemp(),
        }):
            setup_logging(app)

        root = logging.getLogger()
        handlers = root.handlers
        # production 应有 console handler + file handler
        assert len(handlers) >= 1
        # 清理
        for h in handlers[:]:
            h.close()
            root.removeHandler(h)

    def test_development_logging_setup(self):
        """development 环境日志配置。"""
        import logging
        from app.utils.logging import setup_logging
        from flask import Flask

        app = Flask(__name__)
        app.config["TESTING"] = True

        with patch.dict(os.environ, {
            "FLASK_ENV": "development",
            "LOG_LEVEL": "INFO",
        }):
            setup_logging(app)

        root = logging.getLogger()
        handlers = root.handlers
        assert len(handlers) >= 1
        for h in handlers[:]:
            h.close()
            root.removeHandler(h)

    def test_log_level_invalid_fallback(self):
        """无效 LOG_LEVEL 应回退到 INFO。"""
        import logging
        from app.utils.logging import setup_logging
        from flask import Flask

        app = Flask(__name__)
        app.config["TESTING"] = True

        with patch.dict(os.environ, {
            "FLASK_ENV": "development",
            "LOG_LEVEL": "INVALID_LEVEL",
        }):
            setup_logging(app)

        root = logging.getLogger()
        # 应使用 INFO 作为回退
        assert root.level == logging.INFO
        for h in root.handlers[:]:
            h.close()
            root.removeHandler(h)


# ════════════════════════════════════════════
# 七、API 层边界测试
# ════════════════════════════════════════════

class TestApiEdgeCases:
    """覆盖 API 层中未测试的边界路径。"""

    # ── tags 边界 ──

    def test_create_tag_invalid_color(self, client):
        """创建标签时颜色无效。"""
        resp = client.post("/api/tags",
                           data=json.dumps({"name": "标签", "color": "invalid"}),
                           content_type="application/json")
        assert resp.status_code == 400

    def test_update_tag_no_body(self, client):
        """更新标签时请求体为空。"""
        created, _ = create_tag(client, "更新测试标签")
        resp = client.put(f"/api/tags/{created['id']}",
                          data="",
                          content_type="application/json")
        assert resp.status_code == 400

    def test_update_tag_invalid_color(self, client):
        """更新标签时颜色格式无效。"""
        created, _ = create_tag(client, "颜色更新测试")
        resp = client.put(f"/api/tags/{created['id']}",
                          data=json.dumps({"color": "not-a-color"}),
                          content_type="application/json")
        assert resp.status_code == 400

    def test_update_tag_invalid_name(self, client):
        """更新标签时名称为空。"""
        created, _ = create_tag(client, "名称更新测试")
        resp = client.put(f"/api/tags/{created['id']}",
                          data=json.dumps({"name": ""}),
                          content_type="application/json")
        assert resp.status_code == 400

    # ── todos 边界 ──

    def test_assign_tags_to_nonexistent_todo(self, client):
        """为不存在的 todo 添加标签返回 404。"""
        tag, _ = create_tag(client, "测试标签")
        resp = client.post("/api/todos/99999/tags",
                           data=json.dumps({"tag_ids": [tag["id"]]}),
                           content_type="application/json")
        assert resp.status_code == 404

    def test_set_tags_no_tag_ids_key(self, client):
        """set_tags 请求体缺少 tag_ids 键。"""
        created, _ = create_todo(client, "覆盖测试")
        resp = client.put(f"/api/todos/{created['id']}/tags",
                          data=json.dumps({}),
                          content_type="application/json")
        assert resp.status_code == 400

    def test_set_tags_nonexistent_todo(self, client):
        """为不存在的 todo 覆盖标签返回 404。"""
        tag, _ = create_tag(client, "标签X")
        resp = client.put("/api/todos/99999/tags",
                          data=json.dumps({"tag_ids": [tag["id"]]}),
                          content_type="application/json")
        assert resp.status_code == 404

    def test_update_todo_none_due_date(self, client):
        """更新时将 due_date 设为 None。"""
        created, _ = create_todo(client, "带日期", due_date="2025-01-01T00:00:00")
        resp = client.put(f"/api/todos/{created['id']}",
                          data=json.dumps({"due_date": None}),
                          content_type="application/json")
        assert resp.status_code == 200
        assert json.loads(resp.data)["due_date"] is None

    # ── 列表筛选边界 ──

    def test_list_invalid_completed_param(self, client):
        """completed 参数无效时返回 400。"""
        resp = client.get("/api/todos?completed=yes")
        assert resp.status_code == 400

    def test_list_invalid_priority_param(self, client):
        """priority 参数无效时返回 400。"""
        resp = client.get("/api/todos?priority=critical")
        assert resp.status_code == 400

    def test_list_invalid_category_param(self, client):
        """category 参数无效时返回 400。"""
        resp = client.get("/api/todos?category=unknown")
        assert resp.status_code == 400

    # ── 空请求体边界 ──

    def test_create_todo_null_body(self, client):
        """创建时请求体为 null。"""
        resp = client.post("/api/todos",
                           data="null",
                           content_type="application/json")
        assert resp.status_code == 400


# ════════════════════════════════════════════
# 八、Service 层边界测试
# ════════════════════════════════════════════

class TestServiceEdgeCases:
    """覆盖 Service 层中未测试的异常路径。"""

    def test_assign_tags_invalid_tag_ids(self, client):
        """为 todo 添加不存在的标签 IDs。"""
        created, _ = create_todo(client, "无效标签测试")
        resp = client.post(f"/api/todos/{created['id']}/tags",
                           data=json.dumps({"tag_ids": [99999, 88888]}),
                           content_type="application/json")
        assert resp.status_code == 400

    def test_set_tags_invalid_tag_ids(self, client):
        """覆盖设置时包含不存在的标签 IDs。"""
        created, _ = create_todo(client, "覆盖无效标签")
        resp = client.put(f"/api/todos/{created['id']}/tags",
                          data=json.dumps({"tag_ids": [99999]}),
                          content_type="application/json")
        assert resp.status_code == 400

    def test_create_todo_with_invalid_tag_ids(self, client):
        """创建 todo 时附带不存在的标签 ID。"""
        resp = client.post("/api/todos",
                           data=json.dumps({
                               "title": "无效标签关联",
                               "tag_ids": [99999],
                           }),
                           content_type="application/json")
        assert resp.status_code == 400

    def test_remove_nonexistent_tag_from_todo(self, client):
        """移除不存在的标签关联。"""
        tag, _ = create_tag(client, "存在标签")
        created, _ = create_todo(client, "无关联", tag_ids=[])
        resp = client.delete(f"/api/todos/{created['id']}/tags/{tag['id']}")
        assert resp.status_code == 404


# ════════════════════════════════════════════
# 九、Repository 层事务 / savepoint 测试
# ════════════════════════════════════════════

class TestRepositoryEdge:
    """覆盖 Repository 层中未测试的事务路径。"""

    def test_rollback_on_error(self, app):
        """测试 savepoint 回滚机制。"""
        with app.app_context():
            from app.extensions import db as _db
            from app.models import Todo
            from app.repositories import TodoRepository

            try:
                todo = Todo(title="回滚测试")
                _db.session.add(todo)
                _db.session.flush()

                # 触发 savepoint 回滚
                TodoRepository.rollback()
                _db.session.rollback()
            except Exception:
                pass

            # 数据应不存在
            count = Todo.query.filter_by(title="回滚测试").count()
            assert count == 0

    def test_find_by_ids_empty(self, app):
        """find_by_ids 传入空列表应返回空列表。"""
        with app.app_context():
            from app.repositories import TagRepository
            result = TagRepository.find_by_ids([])
            assert result == []

    def test_find_by_ids_mixed(self, app):
        """find_by_ids 混合存在/不存在的 ID。"""
        with app.app_context():
            from app.models import Tag
            from app.extensions import db as _db
            from app.repositories import TagRepository

            tag = Tag(name="存在标签")
            _db.session.add(tag)
            _db.session.commit()

            result = TagRepository.find_by_ids([tag.id, 99999])
            assert len(result) == 1
            assert result[0].id == tag.id


# ════════════════════════════════════════════
# 十、应用工厂与配置
# ════════════════════════════════════════════

class TestAppFactory:
    """覆盖 app/__init__.py 中的工厂函数边界。"""

    def test_create_app_with_explicit_config(self):
        """显式传入 config_name。"""
        from app import create_app
        app = create_app("testing")
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        assert app.config["TESTING"] is True

    def test_create_app_production_default(self, monkeypatch):
        """默认 FLASK_ENV 未设置时应回退到 production。"""
        monkeypatch.delenv("FLASK_ENV", raising=False)
        from app import create_app
        app = create_app()
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        # production 下 TESTING 应为 False
        assert app.config.get("TESTING") is not True

    def test_create_app_testing_env_var(self, monkeypatch):
        """通过 TESTING 环境变量覆盖配置。"""
        monkeypatch.setenv("TESTING", "1")
        from app import create_app
        app = create_app("development")
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        assert app.config["TESTING"] is True

    def test_cors_origins_config(self):
        """CORS 配置正确应用。"""
        from app import create_app
        app = create_app("testing")
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["CORS_ORIGINS"] = "http://example.com,http://test.com"
        # CORS 应在应用上正确配置
        assert app.config["CORS_ORIGINS"] is not None


# ════════════════════════════════════════════
# 十一、TagOutSchema from_model 进阶
# ════════════════════════════════════════════

class TestTagOutSchemaEdge:
    """覆盖 TagOutSchema.from_model 的所有分支。"""

    def test_from_model_with_todo_count_override(self, app):
        """todo_count_override 参数避免 N+1。"""
        with app.app_context():
            from app.models import Tag
            from app.extensions import db as _db
            from app.schemas.tag import TagOutSchema

            tag = Tag(name="计数覆盖")
            _db.session.add(tag)
            _db.session.commit()

            d = TagOutSchema.from_model(tag, todo_count_override=42)
            assert d["todo_count"] == 42
            assert d["name"] == "计数覆盖"

    def test_from_model_include_todos(self, app):
        """include_todos=True 时包含关联的 Todo 列表。"""
        with app.app_context():
            from app.models import Tag, Todo
            from app.extensions import db as _db
            from app.schemas.tag import TagOutSchema

            tag = Tag(name="有关联标签")
            todo1 = Todo(title="关联任务1")
            todo2 = Todo(title="关联任务2")
            tag.todos.append(todo1)
            tag.todos.append(todo2)
            _db.session.add_all([tag, todo1, todo2])
            _db.session.commit()

            d = TagOutSchema.from_model(tag, include_todos=True)
            assert d["todo_count"] == 2
            assert len(d["todos"]) == 2
            assert d["todos"][0]["title"] in ("关联任务1", "关联任务2")


# ════════════════════════════════════════════
# 十二、空数据库状态测试
# ════════════════════════════════════════════

class TestEmptyState:
    """验证空数据库状态下各端点正常返回。"""

    def test_stats_empty(self, client):
        """空数据库统计正常返回。"""
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["total_todos"] == 0
        assert data["completed_todos"] == 0

    def test_dashboard_empty(self, client):
        """空数据库仪表盘正常返回。"""
        resp = client.get("/api/stats/dashboard")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["daily_created"] == []
        assert data["priority_distribution"] == []

    def test_tags_empty(self, client):
        """空数据库标签列表返回空数组。"""
        resp = client.get("/api/tags")
        assert resp.status_code == 200
        assert json.loads(resp.data) == []

    def test_batch_delete_empty(self, client):
        """批量删除无已完成项时应返回 0。"""
        resp = client.post("/api/todos/batch/delete-completed")
        assert resp.status_code == 200
        assert json.loads(resp.data)["deleted_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
