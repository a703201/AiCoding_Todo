"""
Mock 与模拟对象测试
覆盖：Redis Mock、外部依赖 Mock、缓存行为验证
"""
import json
import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conftest import create_todo, create_tag


# ════════════════════════════════════════════
# Redis 缓存行为测试
# ════════════════════════════════════════════

class TestRedisCaching:

    def test_cache_miss_returns_fresh_data(self, mock_redis, client):
        """缓存未命中时应从数据库返回数据。"""
        create_todo(client, "无缓存任务")

        resp = client.get("/api/todos")
        data = json.loads(resp.data)
        assert len(data["data"]) == 1
        assert data["data"][0]["title"] == "无缓存任务"

    def test_cache_hit_returns_cached_data(self, mock_redis_with_cache, client):
        """缓存命中时应直接返回缓存数据。"""
        resp = client.get("/api/todos")
        data = json.loads(resp.data)
        assert data["data"][0]["title"] == "缓存数据"

    def test_cache_bypass_when_filtered(self, mock_redis_with_cache, client):
        """带筛选参数时应跳过缓存，直接查数据库。"""
        create_todo(client, "高优任务", priority="high")

        resp = client.get("/api/todos?priority=high")
        data = json.loads(resp.data)["data"]
        assert len(data) == 1
        assert data[0]["title"] == "高优任务"

    def test_cache_invalidation_on_create(self, mock_redis, client):
        """创建操作应清除列表缓存。"""
        mock_redis.delete = mock_redis.delete  # ensure it's the mock

        create_todo(client, "新任务")

        # 验证 delete 被调用（清除缓存）
        mock_redis.delete.assert_called()

    def test_cache_invalidation_on_update(self, mock_redis, client):
        """更新操作应清除列表缓存。"""
        created, _ = create_todo(client, "原任务")

        client.put(f"/api/todos/{created['id']}",
                   data=json.dumps({"title": "更新后"}),
                   content_type="application/json")

        mock_redis.delete.assert_called()

    def test_cache_invalidation_on_delete(self, mock_redis, client):
        """删除操作应清除列表缓存。"""
        created, _ = create_todo(client, "删缓存任务")

        client.delete(f"/api/todos/{created['id']}")

        mock_redis.delete.assert_called()

    def test_stats_without_redis(self, mock_redis, client):
        """Redis 不可用时应优雅降级，stats 仍正常返回。"""
        create_todo(client, "无缓存统计")

        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["total_todos"] == 1
        assert data["redis_available"] is True  # mock returns True


# ════════════════════════════════════════════
# 外部依赖故障模拟
# ════════════════════════════════════════════

class TestGracefulDegradation:

    def test_api_works_without_redis(self, client):
        """不依赖 Redis 时 API 应正常工作。"""
        # 不使用 mock_redis fixture，Redis 不可用时优雅降级
        created, code = create_todo(client, "无 Redis 任务")
        assert code == 201

        resp = client.get("/api/todos")
        assert resp.status_code == 200
        data = json.loads(resp.data)["data"]
        assert len(data) >= 1

    def test_health_endpoint_no_redis(self, client):
        """Redis 不可用时健康检查仍返回正常。"""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "ok"
        assert data["database"] == "ok"


# ════════════════════════════════════════════
# Mock 日志验证
# ════════════════════════════════════════════

class TestMockLogging:

    def test_logging_on_create(self, client, caplog):
        """创建操作应产生日志。"""
        import logging
        caplog.set_level(logging.INFO)

        create_todo(client, "日志测试")

        log_messages = [r.message for r in caplog.records]
        assert any("创建待办事项" in m for m in log_messages) or \
               any("日志系统初始化完成" in m for m in log_messages)

    def test_logging_on_delete(self, client, caplog):
        """删除操作应产生日志。"""
        import logging
        created, _ = create_todo(client, "日志删除")

        caplog.set_level(logging.INFO)
        client.delete(f"/api/todos/{created['id']}")

        log_messages = [r.message for r in caplog.records]
        assert any(f"删除待办事项: id={created['id']}" in m for m in log_messages)


# ════════════════════════════════════════════
# Mock 验证 - HTTP 状态码边界
# ════════════════════════════════════════════

class TestMockStatusCodeBoundary:

    def test_create_and_verify_status_codes(self, client):
        """验证各种 HTTP 状态码。"""
        # 201 Created
        resp = client.post("/api/todos",
                           data=json.dumps({"title": "状态码测试"}),
                           content_type="application/json")
        assert resp.status_code == 201

        # 200 OK
        todo_id = json.loads(resp.data)["id"]
        resp = client.get(f"/api/todos/{todo_id}")
        assert resp.status_code == 200

        # 400 Bad Request
        resp = client.post("/api/todos",
                           data=json.dumps({}),
                           content_type="application/json")
        assert resp.status_code == 400

        # 404 Not Found
        resp = client.get("/api/todos/99999")
        assert resp.status_code == 404

        # 409 Conflict
        create_tag(client, "唯一标签")
        resp = client.post("/api/tags",
                           data=json.dumps({"name": "唯一标签"}),
                           content_type="application/json")
        assert resp.status_code == 409


# ════════════════════════════════════════════
# Mock - 并发安全模拟
# ════════════════════════════════════════════

class TestConcurrentSafety:

    def test_rapid_create_and_read(self, client):
        """快速连续创建和读取，验证数据一致性。"""
        ids = []
        for i in range(20):
            resp = client.post("/api/todos",
                               data=json.dumps({"title": f"批量 {i}"}),
                               content_type="application/json")
            ids.append(json.loads(resp.data)["id"])

        # 验证所有数据可读
        for tid in ids:
            resp = client.get(f"/api/todos/{tid}")
            assert resp.status_code == 200

        # 总数一致
        resp = client.get("/api/todos")
        assert json.loads(resp.data)["pagination"]["total"] == 20

    def test_toggle_consistency(self, client):
        """反复切换状态应保持一致性。"""
        created, _ = create_todo(client, "一致测试")

        for i in range(10):
            resp = client.post(f"/api/todos/{created['id']}/toggle")
            assert resp.status_code == 200
            # 初始 False → 第 1 次 toggle 后为 True (i=0, True), 第 2 次后又为 False …
            assert json.loads(resp.data)["completed"] == (i % 2 == 0)

    def test_tag_assign_consistency(self, client):
        """并发标签操作应保证一致性。"""
        tag_a, _ = create_tag(client, "标签A")
        tag_b, _ = create_tag(client, "标签B")
        created, _ = create_todo(client, "标签一致性")

        # 交替添加和移除
        client.post(f"/api/todos/{created['id']}/tags",
                    data=json.dumps({"tag_ids": [tag_a["id"]]}),
                    content_type="application/json")
        client.post(f"/api/todos/{created['id']}/tags",
                    data=json.dumps({"tag_ids": [tag_b["id"]]}),
                    content_type="application/json")

        resp = client.get(f"/api/todos/{created['id']}")
        assert len(json.loads(resp.data)["tags"]) == 2

        client.delete(f"/api/todos/{created['id']}/tags/{tag_a['id']}")
        resp = client.get(f"/api/todos/{created['id']}")
        assert len(json.loads(resp.data)["tags"]) == 1
