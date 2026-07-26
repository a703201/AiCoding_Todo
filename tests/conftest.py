"""
测试配置文件（pytest 自动加载）
- 统一 Fixture 管理
- Mock 对象支持
- 测试数据库隔离
"""
import json
import os
import sys
import tempfile
from unittest.mock import Mock, patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db as _db, Todo, Tag


# ════════════════════════════════════════════
# 基础 Fixture
# ════════════════════════════════════════════

@pytest.fixture
def app():
    """创建测试用 Flask 应用，使用独立 SQLite 数据库。"""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })

    with app.app_context():
        _db.create_all()

    yield app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """创建测试客户端。"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """创建 CLI 运行器。"""
    return app.test_cli_runner()


@pytest.fixture
def app_context(app):
    """提供应用上下文（用于直接操作模型）。"""
    with app.app_context():
        yield _db.session


# ════════════════════════════════════════════
# 数据 Fixture
# ════════════════════════════════════════════

@pytest.fixture
def sample_todo_data():
    """示例待办事项字典。"""
    return {
        "title": "测试待办事项",
        "description": "这是一个测试描述",
        "priority": "high",
        "category": "work",
        "due_date": "2025-12-31T23:59:59",
    }


@pytest.fixture
def populated_db(client):
    """预填充数据库（10条数据，含不同状态）。"""
    priorities = ["low", "low", "medium", "medium", "medium", "high", "high", "high", "high", "high"]
    categories = ["personal", "personal", "work", "work", "study", "study", "health", "health", "other", "other"]
    completed_list = [True, False, False, True, False, False, True, False, False, True]

    for i in range(10):
        post_data = {
            "title": f"任务 {i:02d}",
            "description": f"描述 {i}",
            "priority": priorities[i],
            "category": categories[i],
            "due_date": f"2025-{i+1:02d}-01T00:00:00",
        }
        client.post("/api/todos",
                    data=json.dumps(post_data),
                    content_type="application/json")
        if completed_list[i]:
            resp = client.get("/api/todos?search=任务%20{i:02d}")
            data = json.loads(resp.data)["data"]
            if data:
                client.post(f"/api/todos/{data[0]['id']}/toggle")

    return client


@pytest.fixture
def populated_with_tags(client):
    """预填充带标签的数据。"""
    # 创建标签
    tag_data = [
        ("紧急", "#dc3545"),
        ("工作", "#0d6efd"),
        ("学习", "#198754"),
        ("个人", "#ffc107"),
    ]
    tags = {}
    for name, color in tag_data:
        resp = client.post("/api/tags",
                           data=json.dumps({"name": name, "color": color}),
                           content_type="application/json")
        tags[name] = json.loads(resp.data)["id"]

    # 创建待办 + 关联标签
    todos_config = [
        ("学 PostgreSQL", [tags["学习"], tags["紧急"]]),
        ("写周报", [tags["工作"]]),
        ("健身计划", [tags["个人"], tags["紧急"]]),
        ("学习 Docker", [tags["学习"]]),
        ("代码审查", [tags["工作"], tags["紧急"]]),
    ]

    created = []
    for title, tag_ids in todos_config:
        resp = client.post("/api/todos",
                           data=json.dumps({"title": title, "tag_ids": tag_ids}),
                           content_type="application/json")
        created.append(json.loads(resp.data))

    return client, tags, created


# ════════════════════════════════════════════
# Mock Fixture
# ════════════════════════════════════════════

@pytest.fixture
def mock_redis(monkeypatch):
    """Mock Redis 客户端，验证缓存行为。"""
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.get.return_value = None  # 默认缓存未命中
    mock_client.keys.return_value = []

    # Mock Redis 连接
    monkeypatch.setattr("app.get_redis", lambda: mock_client)
    return mock_client


@pytest.fixture
def mock_redis_with_cache(monkeypatch):
    """Mock Redis 客户端，返回缓存数据。"""
    mock_client = MagicMock()
    mock_client.ping.return_value = True

    cached_data = json.dumps({
        "data": [{"id": 1, "title": "缓存数据", "completed": False}],
        "pagination": {"page": 1, "per_page": 20, "total": 1, "pages": 1, "has_next": False, "has_prev": False},
    })
    mock_client.get.return_value = cached_data
    mock_client.keys.return_value = []

    monkeypatch.setattr("app.get_redis", lambda: mock_client)
    return mock_client


# ════════════════════════════════════════════
# 辅助函数
# ════════════════════════════════════════════

def create_todo(client, title="测试待办", **kwargs):
    """创建一条待办事项，支持所有字段，返回 (data, status_code)。"""
    completed = kwargs.pop("completed", None)
    tag_ids = kwargs.pop("tag_ids", None)

    post_data = {"title": title}
    for key in ("description", "priority", "category", "due_date"):
        if key in kwargs:
            post_data[key] = kwargs[key]
    if tag_ids:
        post_data["tag_ids"] = tag_ids

    resp = client.post("/api/todos",
                       data=json.dumps(post_data),
                       content_type="application/json")
    data = json.loads(resp.data)

    if completed and not data.get("completed"):
        todo_id = data["id"]
        if completed:
            client.post(f"/api/todos/{todo_id}/toggle")
            resp2 = client.get(f"/api/todos/{todo_id}")
            data = json.loads(resp2.data)

    return data, resp.status_code


def create_tag(client, name="测试标签", color="#6c757d"):
    """创建标签，返回 (data, status_code)。"""
    resp = client.post("/api/tags",
                       data=json.dumps({"name": name, "color": color}),
                       content_type="application/json")
    return json.loads(resp.data), resp.status_code
