"""
待办事项应用 - 单元测试（数据库增强版）
覆盖：模型关系、标签CRUD、聚合统计、搜索分页、事务、索引查询
"""
import json
import logging
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db as _db, Todo, Tag
from conftest import create_todo, create_tag


# ════════════════════════════════════════════
# 一、创建 (POST /api/todos)
# ════════════════════════════════════════════

class TestCreateTodo:

    def test_create_basic(self, client):
        resp = client.post("/api/todos",
                           data=json.dumps({"title": "学习 Flask"}),
                           content_type="application/json")
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data["title"] == "学习 Flask"
        assert data["completed"] is False
        assert data["priority"] == "medium"
        assert data["category"] == "other"
        assert "id" in data
        assert "created_at" in data

    def test_create_with_all_fields(self, client):
        resp = client.post("/api/todos",
                           data=json.dumps({
                               "title": "完整测试",
                               "description": "详细描述",
                               "priority": "high",
                               "category": "work",
                               "due_date": "2025-12-31T18:00:00",
                           }),
                           content_type="application/json")
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data["title"] == "完整测试"
        assert data["description"] == "详细描述"
        assert data["priority"] == "high"
        assert data["category"] == "work"
        assert data["due_date"] == "2025-12-31T18:00:00"

    def test_create_missing_title(self, client):
        resp = client.post("/api/todos",
                           data=json.dumps({}),
                           content_type="application/json")
        assert resp.status_code == 400
        assert "error" in json.loads(resp.data)

    def test_create_empty_title(self, client):
        resp = client.post("/api/todos",
                           data=json.dumps({"title": "   "}),
                           content_type="application/json")
        assert resp.status_code == 400

    def test_create_title_too_long(self, client):
        resp = client.post("/api/todos",
                           data=json.dumps({"title": "A" * 201}),
                           content_type="application/json")
        assert resp.status_code == 400

    def test_create_title_exact_max_length(self, client):
        resp = client.post("/api/todos",
                           data=json.dumps({"title": "A" * 200}),
                           content_type="application/json")
        assert resp.status_code == 201

    def test_create_invalid_priority(self, client):
        resp = client.post("/api/todos",
                           data=json.dumps({"title": "测试", "priority": "urgent"}),
                           content_type="application/json")
        assert resp.status_code == 400

    def test_create_invalid_category(self, client):
        resp = client.post("/api/todos",
                           data=json.dumps({"title": "测试", "category": "unknown"}),
                           content_type="application/json")
        assert resp.status_code == 400

    def test_create_invalid_due_date(self, client):
        resp = client.post("/api/todos",
                           data=json.dumps({"title": "测试", "due_date": "invalid"}),
                           content_type="application/json")
        assert resp.status_code == 400

    def test_create_all_valid_priorities(self, client):
        for p in ("low", "medium", "high"):
            resp = client.post("/api/todos",
                               data=json.dumps({"title": f"优先级 {p}", "priority": p}),
                               content_type="application/json")
            assert resp.status_code == 201
            assert json.loads(resp.data)["priority"] == p

    def test_create_all_valid_categories(self, client):
        for c in ("personal", "work", "study", "health", "other"):
            resp = client.post("/api/todos",
                               data=json.dumps({"title": f"分类 {c}", "category": c}),
                               content_type="application/json")
            assert resp.status_code == 201
            assert json.loads(resp.data)["category"] == c

    def test_create_no_json_body(self, client):
        resp = client.post("/api/todos",
                           data="not json",
                           content_type="application/json")
        assert resp.status_code == 400


# ════════════════════════════════════════════
# 二、列表（搜索 + 分页 + 筛选 + 排序）
# ════════════════════════════════════════════

class TestListTodos:

    def test_list_empty(self, client):
        resp = client.get("/api/todos")
        assert resp.status_code == 200
        assert json.loads(resp.data)["data"] == []

    def test_list_multiple(self, client):
        create_todo(client, "第一条")
        create_todo(client, "第二条")
        create_todo(client, "第三条")

        resp = client.get("/api/todos")
        data = json.loads(resp.data)["data"]
        assert len(data) == 3
        assert data[0]["title"] == "第三条"

    def test_list_pagination(self, client):
        """测试分页参数。"""
        for i in range(15):
            create_todo(client, f"任务 {i:02d}")

        resp = client.get("/api/todos?page=1&per_page=5")
        result = json.loads(resp.data)
        assert len(result["data"]) == 5
        assert result["pagination"]["total"] == 15
        assert result["pagination"]["pages"] == 3
        assert result["pagination"]["has_next"] is True

        resp2 = client.get("/api/todos?page=3&per_page=5")
        result2 = json.loads(resp2.data)
        assert len(result2["data"]) == 5
        assert result2["pagination"]["has_next"] is False

    def test_search_by_title(self, client):
        """测试全文搜索——按标题。"""
        create_todo(client, "学习 Docker")
        create_todo(client, "学习 K8s")
        create_todo(client, "写代码")

        resp = client.get("/api/todos?search=学习")
        data = json.loads(resp.data)["data"]
        assert len(data) == 2

    def test_search_by_description(self, client):
        """测试全文搜索——按描述。"""
        create_todo(client, "任务A", description="需要学习 Postgres")
        create_todo(client, "任务B", description="复习 Redis")
        create_todo(client, "任务C", description="学习 MySQL")

        resp = client.get("/api/todos?search=Postgres")
        data = json.loads(resp.data)["data"]
        assert len(data) == 1
        assert data[0]["title"] == "任务A"

    def test_filter_completed_true(self, client):
        create_todo(client, "未完成")
        create_todo(client, "已完成", completed=True)

        resp = client.get("/api/todos?completed=true")
        data = json.loads(resp.data)["data"]
        assert len(data) == 1
        assert data[0]["title"] == "已完成"

    def test_filter_completed_false(self, client):
        create_todo(client, "未完成")
        create_todo(client, "已完成", completed=True)

        resp = client.get("/api/todos?completed=false")
        data = json.loads(resp.data)["data"]
        assert len(data) == 1
        assert data[0]["title"] == "未完成"

    def test_filter_priority(self, client):
        create_todo(client, "低优", priority="low")
        create_todo(client, "中优", priority="medium")
        create_todo(client, "高优", priority="high")

        resp = client.get("/api/todos?priority=high")
        data = json.loads(resp.data)["data"]
        assert len(data) == 1
        assert data[0]["priority"] == "high"

    def test_filter_category(self, client):
        create_todo(client, "个人", category="personal")
        create_todo(client, "工作", category="work")

        resp = client.get("/api/todos?category=work")
        data = json.loads(resp.data)["data"]
        assert len(data) == 1
        assert data[0]["category"] == "work"

    def test_filter_due_before(self, client):
        create_todo(client, "今天", due_date="2025-01-01T00:00:00")
        create_todo(client, "明年", due_date="2026-12-31T00:00:00")

        resp = client.get("/api/todos?due_before=2025-06-01T00:00:00")
        data = json.loads(resp.data)["data"]
        assert len(data) == 1
        assert data[0]["title"] == "今天"

    def test_filter_due_before_invalid(self, client):
        resp = client.get("/api/todos?due_before=bad-date")
        assert resp.status_code == 400

    def test_filter_combined(self, client):
        create_todo(client, "匹配项", priority="high", category="work", completed=False)
        create_todo(client, "不匹配-已完成", priority="high", category="work", completed=True)
        create_todo(client, "不匹配-低优", priority="low", category="work")

        resp = client.get("/api/todos?priority=high&category=work&completed=false")
        data = json.loads(resp.data)["data"]
        assert len(data) == 1
        assert data[0]["title"] == "匹配项"

    def test_sort_by_title_asc(self, client):
        create_todo(client, "C 任务")
        create_todo(client, "A 任务")
        create_todo(client, "B 任务")

        resp = client.get("/api/todos?sort_by=title&sort_order=asc")
        data = json.loads(resp.data)["data"]
        assert data[0]["title"] == "A 任务"
        assert data[2]["title"] == "C 任务"

    def test_sort_by_priority(self, client):
        create_todo(client, "低", priority="low")
        create_todo(client, "高", priority="high")
        create_todo(client, "中", priority="medium")

        resp = client.get("/api/todos?sort_by=priority&sort_order=desc")
        data = json.loads(resp.data)["data"]
        # alphabetical desc: medium, low, high
        assert data[0]["priority"] == "medium"


# ════════════════════════════════════════════
# 三、查询单个
# ════════════════════════════════════════════

class TestGetTodo:

    def test_get_existing(self, client):
        created, _ = create_todo(client, "存在的任务")
        resp = client.get(f"/api/todos/{created['id']}")
        assert resp.status_code == 200
        assert json.loads(resp.data)["title"] == "存在的任务"

    def test_get_non_existing(self, client):
        resp = client.get("/api/todos/99999")
        assert resp.status_code == 404

    def test_get_invalid_id(self, client):
        resp = client.get("/api/todos/abc")
        assert resp.status_code == 404


# ════════════════════════════════════════════
# 四、更新
# ════════════════════════════════════════════

class TestUpdateTodo:

    def test_update_title(self, client):
        created, _ = create_todo(client, "原始标题")
        resp = client.put(f"/api/todos/{created['id']}",
                          data=json.dumps({"title": "新标题"}),
                          content_type="application/json")
        assert resp.status_code == 200
        assert json.loads(resp.data)["title"] == "新标题"

    def test_update_multiple_fields(self, client):
        created, _ = create_todo(client, "原始")
        resp = client.put(f"/api/todos/{created['id']}",
                          data=json.dumps({
                              "title": "更新标题",
                              "priority": "high",
                              "category": "study",
                              "description": "新描述",
                          }),
                          content_type="application/json")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["title"] == "更新标题"
        assert data["priority"] == "high"
        assert data["category"] == "study"

    def test_update_empty_title(self, client):
        created, _ = create_todo(client, "原始")
        resp = client.put(f"/api/todos/{created['id']}",
                          data=json.dumps({"title": "   "}),
                          content_type="application/json")
        assert resp.status_code == 400

    def test_update_invalid_priority(self, client):
        created, _ = create_todo(client, "原始")
        resp = client.put(f"/api/todos/{created['id']}",
                          data=json.dumps({"priority": "critical"}),
                          content_type="application/json")
        assert resp.status_code == 400

    def test_update_invalid_category(self, client):
        created, _ = create_todo(client, "原始")
        resp = client.put(f"/api/todos/{created['id']}",
                          data=json.dumps({"category": "invalid"}),
                          content_type="application/json")
        assert resp.status_code == 400

    def test_update_non_existing(self, client):
        resp = client.put("/api/todos/99999",
                          data=json.dumps({"title": "不存在"}),
                          content_type="application/json")
        assert resp.status_code == 404

    def test_update_no_body(self, client):
        created, _ = create_todo(client, "测试")
        resp = client.put(f"/api/todos/{created['id']}",
                          data="",
                          content_type="application/json")
        assert resp.status_code == 400

    def test_update_clear_due_date(self, client):
        created, _ = create_todo(client, "有日期", due_date="2025-01-01T00:00:00")
        resp = client.put(f"/api/todos/{created['id']}",
                          data=json.dumps({"due_date": None}),
                          content_type="application/json")
        assert resp.status_code == 200
        assert json.loads(resp.data)["due_date"] is None


# ════════════════════════════════════════════
# 五、删除
# ════════════════════════════════════════════

class TestDeleteTodo:

    def test_delete_existing(self, client):
        created, _ = create_todo(client, "待删除")
        resp = client.delete(f"/api/todos/{created['id']}")
        assert resp.status_code == 200
        assert "已删除" in json.loads(resp.data)["message"]
        resp = client.get(f"/api/todos/{created['id']}")
        assert resp.status_code == 404

    def test_delete_non_existing(self, client):
        resp = client.delete("/api/todos/99999")
        assert resp.status_code == 404

    def test_delete_twice(self, client):
        created, _ = create_todo(client, "删除一次")
        client.delete(f"/api/todos/{created['id']}")
        resp = client.delete(f"/api/todos/{created['id']}")
        assert resp.status_code == 404


# ════════════════════════════════════════════
# 六、切换状态 + 批量操作
# ════════════════════════════════════════════

class TestToggleTodo:

    def test_toggle_from_false_to_true(self, client):
        created, _ = create_todo(client, "切换测试")
        assert created["completed"] is False
        resp = client.post(f"/api/todos/{created['id']}/toggle")
        assert resp.status_code == 200
        assert json.loads(resp.data)["completed"] is True

    def test_toggle_from_true_to_false(self, client):
        created, _ = create_todo(client, "已完成", completed=True)
        assert created["completed"] is True
        resp = client.post(f"/api/todos/{created['id']}/toggle")
        assert resp.status_code == 200
        assert json.loads(resp.data)["completed"] is False

    def test_toggle_non_existing(self, client):
        resp = client.post("/api/todos/99999/toggle")
        assert resp.status_code == 404

    def test_toggle_multiple_times(self, client):
        created, _ = create_todo(client, "反复切换")
        for expected in (True, False, True):
            resp = client.post(f"/api/todos/{created['id']}/toggle")
            assert json.loads(resp.data)["completed"] is expected


class TestBatchOperations:

    def test_batch_delete_completed(self, client):
        create_todo(client, "未完成")
        create_todo(client, "已完成1", completed=True)
        create_todo(client, "已完成2", completed=True)

        resp = client.post("/api/todos/batch/delete-completed")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["deleted_count"] == 2

        list_data = json.loads(client.get("/api/todos").data)["data"]
        assert len(list_data) == 1


# ════════════════════════════════════════════
# 七、标签 CRUD
# ════════════════════════════════════════════

class TestTagCRUD:

    def test_create_tag(self, client):
        resp = client.post("/api/tags",
                           data=json.dumps({"name": "紧急", "color": "#dc3545"}),
                           content_type="application/json")
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data["name"] == "紧急"
        assert data["color"] == "#dc3545"
        assert data["todo_count"] == 0

    def test_create_duplicate_tag(self, client):
        create_tag(client, "紧急")
        resp = client.post("/api/tags",
                           data=json.dumps({"name": "紧急"}),
                           content_type="application/json")
        assert resp.status_code == 409
        assert "已存在" in json.loads(resp.data)["error"]

    def test_create_tag_empty_name(self, client):
        resp = client.post("/api/tags",
                           data=json.dumps({"name": ""}),
                           content_type="application/json")
        assert resp.status_code == 400

    def test_create_tag_name_too_long(self, client):
        resp = client.post("/api/tags",
                           data=json.dumps({"name": "A" * 51}),
                           content_type="application/json")
        assert resp.status_code == 400

    def test_list_tags(self, client):
        create_tag(client, "标签A")
        create_tag(client, "标签B")
        resp = client.get("/api/tags")
        data = json.loads(resp.data)
        assert len(data) == 2

    def test_get_tag(self, client):
        created, _ = create_tag(client, "查看标签")
        resp = client.get(f"/api/tags/{created['id']}")
        data = json.loads(resp.data)
        assert data["name"] == "查看标签"
        assert "todos" in data

    def test_get_tag_not_found(self, client):
        resp = client.get("/api/tags/99999")
        assert resp.status_code == 404

    def test_update_tag(self, client):
        created, _ = create_tag(client, "旧名称")
        resp = client.put(f"/api/tags/{created['id']}",
                          data=json.dumps({"name": "新名称", "color": "#000000"}),
                          content_type="application/json")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["name"] == "新名称"
        assert data["color"] == "#000000"

    def test_update_tag_duplicate_name(self, client):
        create_tag(client, "标签A")
        created, _ = create_tag(client, "标签B")
        resp = client.put(f"/api/tags/{created['id']}",
                          data=json.dumps({"name": "标签A"}),
                          content_type="application/json")
        assert resp.status_code == 409

    def test_delete_tag(self, client):
        created, _ = create_tag(client, "待删除标签")
        resp = client.delete(f"/api/tags/{created['id']}")
        assert resp.status_code == 200
        resp2 = client.get(f"/api/tags/{created['id']}")
        assert resp2.status_code == 404

    def test_delete_tag_not_found(self, client):
        resp = client.delete("/api/tags/99999")
        assert resp.status_code == 404


# ════════════════════════════════════════════
# 八、待办 ↔ 标签关联
# ════════════════════════════════════════════

class TestTodoTagsAssociation:

    def test_create_todo_with_tags(self, client):
        tag1, _ = create_tag(client, "紧急")
        tag2, _ = create_tag(client, "工作")

        resp = client.post("/api/todos",
                           data=json.dumps({
                               "title": "带标签的任务",
                               "tag_ids": [tag1["id"], tag2["id"]],
                           }),
                           content_type="application/json")
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert len(data["tags"]) == 2
        tag_names = [t["name"] for t in data["tags"]]
        assert "紧急" in tag_names
        assert "工作" in tag_names

    def test_assign_tags(self, client):
        created, _ = create_todo(client, "待标签")
        tag, _ = create_tag(client, "学习")

        resp = client.post(f"/api/todos/{created['id']}/tags",
                           data=json.dumps({"tag_ids": [tag["id"]]}),
                           content_type="application/json")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data["tags"]) == 1
        assert data["tags"][0]["name"] == "学习"

    def test_assign_tags_no_body(self, client):
        created, _ = create_todo(client, "测试")
        resp = client.post(f"/api/todos/{created['id']}/tags",
                           data=json.dumps({}),
                           content_type="application/json")
        assert resp.status_code == 400

    def test_assign_duplicate_tags(self, client):
        created, _ = create_todo(client, "重复标签测试")
        tag, _ = create_tag(client, "重点")

        # 第一次添加
        client.post(f"/api/todos/{created['id']}/tags",
                    data=json.dumps({"tag_ids": [tag["id"]]}),
                    content_type="application/json")
        # 第二次添加相同标签（不应重复）
        resp = client.post(f"/api/todos/{created['id']}/tags",
                           data=json.dumps({"tag_ids": [tag["id"]]}),
                           content_type="application/json")
        data = json.loads(resp.data)
        assert len(data["tags"]) == 1

    def test_remove_tag_from_todo(self, client):
        tag, _ = create_tag(client, "可移除")
        created, _ = create_todo(client, "带标签任务", tag_ids=[tag["id"]])

        resp = client.delete(f"/api/todos/{created['id']}/tags/{tag['id']}")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data["tags"]) == 0

    def test_remove_nonexistent_tag(self, client):
        created, _ = create_todo(client, "无标签")
        resp = client.delete(f"/api/todos/{created['id']}/tags/99999")
        assert resp.status_code == 404

    def test_set_tags_overwrite(self, client):
        tag1, _ = create_tag(client, "标签A")
        tag2, _ = create_tag(client, "标签B")
        tag3, _ = create_tag(client, "标签C")
        created, _ = create_todo(client, "覆盖测试", tag_ids=[tag1["id"], tag2["id"]])

        # 覆盖为仅 tag3
        resp = client.put(f"/api/todos/{created['id']}/tags",
                          data=json.dumps({"tag_ids": [tag3["id"]]}),
                          content_type="application/json")
        data = json.loads(resp.data)
        assert len(data["tags"]) == 1
        assert data["tags"][0]["name"] == "标签C"

    def test_set_tags_clear_all(self, client):
        tag, _ = create_tag(client, "标签")
        created, _ = create_todo(client, "清空测试", tag_ids=[tag["id"]])

        resp = client.put(f"/api/todos/{created['id']}/tags",
                          data=json.dumps({"tag_ids": []}),
                          content_type="application/json")
        data = json.loads(resp.data)
        assert len(data["tags"]) == 0

    def test_cascade_delete_tag(self, client):
        """删除标签后，关联自动清除。"""
        tag, _ = create_tag(client, "待删除标签")
        created, _ = create_todo(client, "关联任务", tag_ids=[tag["id"]])

        client.delete(f"/api/tags/{tag['id']}")
        resp = client.get(f"/api/todos/{created['id']}")
        data = json.loads(resp.data)
        assert len(data["tags"]) == 0

    def test_get_tag_with_associated_todos(self, client):
        tag, _ = create_tag(client, "有任务的标签")
        create_todo(client, "任务1", tag_ids=[tag["id"]])
        create_todo(client, "任务2", tag_ids=[tag["id"]])

        resp = client.get(f"/api/tags/{tag['id']}")
        data = json.loads(resp.data)
        assert len(data["todos"]) == 2


# ════════════════════════════════════════════
# 九、聚合统计
# ════════════════════════════════════════════

class TestStatistics:

    def test_stats_endpoint(self, client):
        create_todo(client, "高优工作", priority="high", category="work")
        create_todo(client, "中优学习", priority="medium", category="study")
        create_todo(client, "已完成", priority="low", category="personal", completed=True)

        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["total_todos"] == 3
        assert data["completed_todos"] == 1
        assert "by_category_priority" in data
        assert "by_completion" in data

    def test_dashboard_endpoint(self, client):
        create_todo(client, "任务1", priority="high", category="work")
        create_todo(client, "任务2", priority="medium", category="study")
        create_todo(client, "任务3", priority="low", category="personal", completed=True)

        resp = client.get("/api/stats/dashboard")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "daily_created" in data
        assert "priority_distribution" in data
        assert "category_stats" in data
        assert "top_tags" in data

        # priority_distribution 应有三个优先级条目
        assert len(data["priority_distribution"]) == 3

        # 验证完成率
        for item in data["priority_distribution"]:
            if item["priority"] == "low":
                assert item["completion_rate"] == 100.0

    def test_dashboard_with_tags(self, client):
        """测试标签使用频率统计。"""
        tag, _ = create_tag(client, "常用标签")
        for i in range(3):
            create_todo(client, f"任务{i}", tag_ids=[tag["id"]])

        resp = client.get("/api/stats/dashboard")
        data = json.loads(resp.data)
        # 至少有一个标签统计
        assert len(data["top_tags"]) >= 1
        top_tag = data["top_tags"][0]
        assert top_tag["usage_count"] == 3


# ════════════════════════════════════════════
# 十、模型测试（关系 + 索引）
# ════════════════════════════════════════════

class TestTodoModel:

    def test_to_dict(self, app):
        with app.app_context():
            todo = Todo(
                title="序列化测试",
                description="描述",
                priority="high",
                category="work",
            )
            _db.session.add(todo)
            _db.session.commit()

            d = todo.to_dict()
            assert d["title"] == "序列化测试"
            assert d["priority"] == "high"
            assert d["category"] == "work"
            assert d["completed"] is False
            assert d["due_date"] is None
            assert d["tags"] == []

    def test_default_values(self, app):
        with app.app_context():
            todo = Todo(title="默认值测试")
            _db.session.add(todo)
            _db.session.commit()
            assert todo.completed is False
            assert todo.priority == "medium"
            assert todo.category == "other"
            assert todo.description == ""

    def test_tag_relationship(self, app):
        """测试 Todo ↔ Tag 多对多关系。"""
        with app.app_context():
            todo = Todo(title="关系测试")
            tag1 = Tag(name="关系标签1")
            tag2 = Tag(name="关系标签2")
            todo.tags = [tag1, tag2]
            _db.session.add_all([todo, tag1, tag2])
            _db.session.commit()

            # 正向：todo.tags
            assert len(todo.tags) == 2
            assert tag1 in todo.tags and tag2 in todo.tags

            # 反向：tag.todos
            assert tag1.todos.count() == 1
            assert tag1.todos.first().title == "关系测试"

    def test_tag_unique_constraint(self, app):
        """测试标签名称唯一约束。"""
        import sqlite3
        with app.app_context():
            tag1 = Tag(name="唯一标签")
            _db.session.add(tag1)
            _db.session.commit()

            tag2 = Tag(name="唯一标签")
            _db.session.add(tag2)
            with pytest.raises(Exception):
                _db.session.commit()


# ════════════════════════════════════════════

class TestTagModel:

    def test_tag_to_dict(self, app):
        with app.app_context():
            tag = Tag(name="模型标签", color="#ff0000")
            _db.session.add(tag)
            _db.session.commit()
            d = tag.to_dict()
            assert d["name"] == "模型标签"
            assert d["color"] == "#ff0000"
            assert d["todo_count"] == 0

    def test_tag_todo_count(self, app):
        with app.app_context():
            tag = Tag(name="计数标签")
            _db.session.add(tag)
            _db.session.commit()

            todo1 = Todo(title="任务1")
            todo2 = Todo(title="任务2")
            todo1.tags.append(tag)
            todo2.tags.append(tag)
            _db.session.add_all([todo1, todo2])
            _db.session.commit()

            assert tag.to_dict()["todo_count"] == 2


# ════════════════════════════════════════════
# 十一、集成测试
# ════════════════════════════════════════════

class TestIntegration:

    def test_full_crud_flow(self, client):
        # 创建标签
        tag, _ = create_tag(client, "集成标签")
        # 创建
        created, code = create_todo(client, "集成测试任务",
                                    priority="high",
                                    category="work",
                                    due_date="2025-07-26T12:00:00",
                                    tag_ids=[tag["id"]])
        assert code == 201
        todo_id = created["id"]

        # 列表含标签
        resp = client.get("/api/todos")
        todos_with_id = [t for t in json.loads(resp.data)["data"] if t["id"] == todo_id]
        assert len(todos_with_id) == 1
        assert len(todos_with_id[0]["tags"]) == 1

        # 查询单个
        resp = client.get(f"/api/todos/{todo_id}")
        assert resp.status_code == 200

        # 更新
        resp = client.put(f"/api/todos/{todo_id}",
                          data=json.dumps({"title": "已更新", "priority": "low"}),
                          content_type="application/json")
        assert resp.status_code == 200

        # 切换
        client.post(f"/api/todos/{todo_id}/toggle")

        # 删除
        resp = client.delete(f"/api/todos/{todo_id}")
        assert resp.status_code == 200
        assert client.get(f"/api/todos/{todo_id}").status_code == 404

    def test_search_and_filter_together(self, client):
        create_todo(client, "学习 Python", description="后端开发", priority="high", category="study")
        create_todo(client, "学习 React", description="前端开发", priority="low", category="study")
        create_todo(client, "写周报", description="工作汇报", priority="medium", category="work")

        resp = client.get("/api/todos?search=学习&priority=high")
        data = json.loads(resp.data)["data"]
        assert len(data) == 1
        assert data[0]["title"] == "学习 Python"


# ════════════════════════════════════════════
# 十二、错误处理
# ════════════════════════════════════════════

class TestErrorHandling:

    def test_404_page(self, client):
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404
        assert "error" in json.loads(resp.data)

    def test_405_method_not_allowed(self, client):
        resp = client.put("/api/todos")
        assert resp.status_code in (405, 404)

    def test_invalid_json(self, client):
        created, _ = create_todo(client, "测试")
        resp = client.put(f"/api/todos/{created['id']}",
                          data="not a json{{{",
                          content_type="application/json")
        assert resp.status_code in (400, 500)

    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "ok"
        assert "database" in data


# ════════════════════════════════════════════
# 十三、数据库事务
# ════════════════════════════════════════════

class TestTransactions:

    def test_rollback_on_validation_error(self, client):
        """验证输入校验失败时不创建记录（隐式事务回滚）。"""
        create_todo(client, "第一条")
        client.post("/api/todos",
                    data=json.dumps({"title": ""}),
                    content_type="application/json")
        resp = client.get("/api/todos")
        data = json.loads(resp.data)["data"]
        assert len(data) == 1

    def test_bulk_create_and_filter(self, client):
        categories = ["personal", "work", "study", "health", "other"]
        for i, cat in enumerate(categories):
            create_todo(client, f"任务 {i}", category=cat,
                        priority="low" if i % 2 == 0 else "high")

        resp = client.get("/api/todos?category=work")
        assert len(json.loads(resp.data)["data"]) == 1

        resp = client.get("/api/todos?priority=high")
        # i=1(work), i=3(health) => 2 个 high
        assert len(json.loads(resp.data)["data"]) == 2

    def test_savepoint_transaction(self, app):
        """测试 savepoint 事务：创建时附带不存在的 tag 应该能处理。"""
        with app.app_context():
            try:
                todo = Todo(title="savepoint 测试")
                _db.session.add(todo)

                # 嵌套 savepoint
                savepoint = _db.session.begin_nested()
                invalid_tag = Tag(name="savepoint-tag")
                _db.session.add(invalid_tag)
                savepoint.commit()

                _db.session.commit()
                assert Tag.query.filter_by(name="savepoint-tag").count() == 1
            except Exception:
                _db.session.rollback()
                pytest.fail("savepoint 事务不应失败")

    def test_per_page_limit(self, client):
        """测试 per_page 参数限制（1-100）。"""
        for i in range(10):
            create_todo(client, f"任务 {i}")

        # 超出上限应被限制为 100
        resp = client.get("/api/todos?per_page=500")
        assert resp.status_code == 200

        # 小于 1 应被限制为 1
        resp = client.get("/api/todos?per_page=0")
        assert resp.status_code == 200


# ════════════════════════════════════════════
# 十四、监控与度量
# ════════════════════════════════════════════

class TestMetricsAndHealth:

    def test_health_endpoint_basic(self, client):
        """测试基本健康检查。"""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "ok"
        assert "database" in data
        assert "redis" in data

    def test_health_with_data(self, client):
        """健康检查包含数据统计。"""
        create_todo(client, "任务1")
        create_todo(client, "任务2", completed=True)

        resp = client.get("/health")
        data = json.loads(resp.data)
        assert data["total_todos"] == 2
        assert "total_tags" in data

    def test_health_disk_memory_info(self, client):
        """健康检查包含磁盘和内存信息。"""
        resp = client.get("/health")
        data = json.loads(resp.data)
        assert "disk_usage_percent" in data
        assert "memory_usage_percent" in data

    def test_metrics_endpoint(self, client):
        """Prometheus 指标端点测试。"""
        create_todo(client, "指标测试1", priority="high")
        create_todo(client, "指标测试2", priority="low", completed=True)

        resp = client.get("/metrics")
        assert resp.status_code == 200
        content = resp.data.decode("utf-8")

        # 应包含基本指标
        assert "todo_total" in content
        assert "todo_completed" in content
        assert "todo_pending" in content
        assert 'todo_by_priority{priority="high"}' in content
        assert 'todo_by_priority{priority="low"}' in content
        assert "todo_app_info" in content
        assert "redis_available" in content

    def test_metrics_content_type(self, client):
        """指标端点返回 text/plain 格式。"""
        resp = client.get("/metrics")
        assert "text/plain" in resp.content_type

    def test_metrics_empty_state(self, client):
        """空数据库时指标端点正常返回。"""
        resp = client.get("/metrics")
        assert resp.status_code == 200
        content = resp.data.decode("utf-8")
        assert "todo_total 0" in content

    def test_metrics_with_tags(self, client):
        """指标包含标签统计。"""
        create_tag(client, "标签A")
        create_tag(client, "标签B")

        resp = client.get("/metrics")
        content = resp.data.decode("utf-8")
        assert "todo_tags_total 2" in content


# ════════════════════════════════════════════
# 十五、部署配置验证
# ════════════════════════════════════════════

class TestDeploymentConfig:

    def test_create_app_factory(self):
        """测试应用工厂模式（Gunicorn 入口兼容性）。"""
        from app import create_app
        app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        })
        with app.test_client() as client:
            resp = client.get("/health")
            assert resp.status_code == 200

    def test_environment_variables(self):
        """测试环境变量默认值。"""
        assert os.getenv("FLASK_ENV", "production") in ("production", "development")

    def test_app_logger_configured(self, app):
        """测试日志系统已配置。"""
        assert app.logger is not None
        assert len(app.logger.handlers) > 0 or len(logging.getLogger().handlers) > 0

    def test_error_handlers_registered(self, app):
        """测试错误处理器已注册。"""
        with app.test_client() as c:
            # 404
            resp = c.get("/nonexistent-route-for-test")
            assert resp.status_code == 404
            data = json.loads(resp.data)
            assert "error" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
