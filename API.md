# AiCoding Todo API 接口文档

> 版本：1.4.0 | 基准路径：`http://localhost:5000` | 数据格式：JSON

---

## 目录

- [通用说明](#通用说明)
- [1. 页面与监控](#1-页面与监控)
  - [GET /](#get-)
  - [GET /health](#get-health)
  - [GET /metrics](#get-metrics)
- [2. 待办事项](#2-待办事项)
  - [GET /api/todos](#get-apitodos)
  - [POST /api/todos](#post-apitodos)
  - [GET /api/todos/:id](#get-apitodosid)
  - [PUT /api/todos/:id](#put-apitodosid)
  - [DELETE /api/todos/:id](#delete-apitodosid)
  - [POST /api/todos/:id/toggle](#post-apitodosidtoggle)
  - [POST /api/todos/batch/delete-completed](#post-apitodosbatchdelete-completed)
- [3. 待办 ↔ 标签关联](#3-待办--标签关联)
  - [POST /api/todos/:id/tags](#post-apitodosidtags)
  - [PUT /api/todos/:id/tags](#put-apitodosidtags)
  - [DELETE /api/todos/:id/tags/:tag_id](#delete-apitodosidtagstag_id)
- [4. 标签](#4-标签)
  - [GET /api/tags](#get-apitags)
  - [POST /api/tags](#post-apitags)
  - [GET /api/tags/:id](#get-apitagsid)
  - [PUT /api/tags/:id](#put-apitagsid)
  - [DELETE /api/tags/:id](#delete-apitagsid)
- [5. 统计](#5-统计)
  - [GET /api/stats](#get-apistats)
  - [GET /api/stats/dashboard](#get-apistatsdashboard)
- [附录](#附录)

---

## 通用说明

### 请求格式

- `Content-Type: application/json`（除 `GET` 和 `/metrics` 外）
- `GET` 请求参数通过 Query String 传递

### 成功响应格式

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

### 错误响应格式

```json
{
  "error": "错误描述信息"
}
```

### 常用状态码

| 状态码 | 含义 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误（ValidationException） |
| 404 | 资源未找到（NotFoundException） |
| 409 | 资源冲突（ConflictException，如标签名重复） |
| 422 | 业务逻辑错误（BusinessException） |
| 500 | 服务器内部错误 |
| 503 | 服务降级（数据库不可用 / 资源不足） |

---

## 1. 页面与监控

### GET /

前端单页应用入口，返回 Todo 管理界面。

**响应**：`text/html`（渲染 `index.html`）

---

### GET /health

增强健康检查，返回数据库、Redis、磁盘、内存状态。

**响应示例**：

```json
{
  "status": "ok",
  "database": "ok",
  "redis": "ok",
  "disk_usage_percent": 45.2,
  "memory_usage_percent": 62.1,
  "total_todos": 128,
  "total_tags": 15
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | `ok` 或 `degraded` |
| `database` | string | `ok` 或 `error` |
| `redis` | string | `ok` 或 `unavailable` |
| `disk_usage_percent` | float/string | 磁盘使用率，异常时为 `"unknown"` |
| `memory_usage_percent` | float/string | 内存使用率，异常时为 `"unknown"` |
| `total_todos` | int | 待办总数 |
| `total_tags` | int | 标签总数 |

**降级条件**（默认阈值可通过环境变量调整）：

- 磁盘 > `HEALTH_DISK_THRESHOLD`%（默认 90）
- 内存 > `HEALTH_MEM_THRESHOLD`%（默认 95）
- 数据库连接失败
- Redis 不可用不触发降级

**状态码**：200（ok）或 503（degraded）

---

### GET /metrics

Prometheus 兼容指标端点。

**响应**：`text/plain; charset=utf-8`

**指标列表**：

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `todo_app_info` | gauge | 应用信息（版本、Python 版本） |
| `todo_total` | gauge | 待办事项总数 |
| `todo_completed` | gauge | 已完成待办数 |
| `todo_pending` | gauge | 未完成待办数 |
| `todo_by_priority` | gauge | 按优先级分布（labels: `priority`） |
| `todo_tags_total` | gauge | 标签总数 |
| `process_memory_usage_bytes` | gauge | 内存使用量 |
| `process_cpu_percent` | gauge | CPU 使用率 |
| `redis_available` | gauge | Redis 可用性（1=可用, 0=不可用） |

---

## 2. 待办事项

### 数据模型

```json
{
  "id": 1,
  "title": "完成周报",
  "description": "整理本周工作内容",
  "completed": false,
  "priority": "high",
  "category": "work",
  "due_date": "2026-07-28T18:00:00",
  "created_at": "2026-07-26T10:30:00",
  "updated_at": "2026-07-26T10:30:00",
  "tags": [
    {"id": 1, "name": "紧急", "color": "#dc3545", "created_at": "...", "todo_count": 3}
  ]
}
```

**字段约束**：

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `title` | string | 创建时必填 | 1~200 字符 |
| `description` | string | 否 | 默认 `""` |
| `completed` | bool | 否 | 默认 `false` |
| `priority` | string | 否 | `low` / `medium` / `high`（默认 `medium`） |
| `category` | string | 否 | `personal` / `work` / `study` / `health` / `other`（默认 `other`） |
| `due_date` | string (ISO 8601) | 否 | 如 `2026-07-28T18:00:00`，`null` 表示无截止日期 |
| `tag_ids` | int[] | 否 | 仅在创建时支持 |

---

### GET /api/todos

获取待办列表（支持搜索、筛选、排序、分页，含缓存）。

**查询参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `search` | string | — | 模糊搜索标题和描述 |
| `completed` | string | — | 完成状态筛选：`true`/`false`/`0`/`1` |
| `priority` | string | — | 优先级筛选：`low`/`medium`/`high` |
| `category` | string | — | 分类筛选：`personal`/`work`/`study`/`health`/`other` |
| `due_before` | string (ISO) | — | 截止日期不晚于指定时间 |
| `sort_by` | string | `created_at` | 排序字段：`created_at`/`updated_at`/`due_date`/`priority`/`title` |
| `sort_order` | string | `desc` | 排序方向：`asc`/`desc` |
| `page` | int | `1` | 页码（最小 1） |
| `per_page` | int | `20` | 每页数量（1~100） |

> **注意**：`priority` 排序按权重（high → medium → low），非字母序。

**响应示例**：

```json
{
  "data": [
    {
      "id": 1,
      "title": "完成周报",
      "description": "",
      "completed": false,
      "priority": "high",
      "category": "work",
      "due_date": "2026-07-28T18:00:00",
      "created_at": "2026-07-26T10:30:00",
      "updated_at": "2026-07-26T10:30:00",
      "tags": []
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 1,
    "pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

**缓存行为**：无筛选参数时缓存 30 秒（可配置 `CACHE_TTL`）。

---

### POST /api/todos

创建待办事项。

**请求体**：

```json
{
  "title": "完成周报",
  "description": "整理本周工作内容",
  "priority": "high",
  "category": "work",
  "due_date": "2026-07-28T18:00:00",
  "tag_ids": [1, 2]
}
```

**响应**：201 Created，返回完整的 Todo 对象。

---

### GET /api/todos/:id

查询单个待办事项。

**响应**：Todo 对象。

**错误**：404 — 资源未找到。

---

### PUT /api/todos/:id

更新待办事项（部分更新，仅传需要修改的字段）。

**请求体**（所有字段可选）：

```json
{
  "title": "更新后的标题",
  "description": "新描述",
  "completed": true,
  "priority": "low",
  "category": "personal",
  "due_date": null
}
```

> `due_date` 传 `null` 可清除截止日期。

**响应**：更新后的 Todo 对象。

**错误**：400 / 404

---

### DELETE /api/todos/:id

删除待办事项（自动级联解除标签关联）。

**响应**：

```json
{"message": "待办事项已删除"}
```

---

### POST /api/todos/:id/toggle

切换待办事项的完成状态（`completed` 取反）。

**请求体**：无。

**响应**：更新后的 Todo 对象。

---

### POST /api/todos/batch/delete-completed

批量删除所有已完成的待办事项。

**请求体**：无。

**响应**：

```json
{
  "message": "已删除 5 条已完成事项",
  "deleted_count": 5
}
```

---

## 3. 待办 ↔ 标签关联

### POST /api/todos/:id/tags

为待办事项添加标签（追加模式）。

**请求体**：

```json
{
  "tag_ids": [1, 2, 3]
}
```

**响应**：更新后的 Todo 对象（含 `tags` 数组）。

**错误**：400 — `tag_ids` 缺失或标签不存在；404 — 待办不存在。

---

### PUT /api/todos/:id/tags

覆盖设置待办事项的标签（替换模式）。

**请求体**：

```json
{
  "tag_ids": [1, 2]
}
```

> 传空数组 `[]` 可清除所有标签。

**响应**：更新后的 Todo 对象。

---

### DELETE /api/todos/:id/tags/:tag_id

移除待办事项的某个标签。

**响应**：更新后的 Todo 对象。

**错误**：404 — 待办、标签或关联不存在。

---

## 4. 标签

### 数据模型

```json
{
  "id": 1,
  "name": "紧急",
  "color": "#dc3545",
  "created_at": "2026-07-26T10:30:00",
  "todo_count": 3
}
```

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `name` | string | 创建时必填 | 1~50 字符，全局唯一 |
| `color` | string | 否 | hex 格式 `#RRGGBB` 或 `#RGB`，默认 `#6c757d` |

---

### GET /api/tags

获取所有标签列表（含每个标签关联的待办数量，批量聚合避免 N+1）。

**响应示例**：

```json
[
  {"id": 1, "name": "紧急", "color": "#dc3545", "created_at": "2026-07-26T10:30:00", "todo_count": 5},
  {"id": 2, "name": "工作", "color": "#0d6efd", "created_at": "2026-07-26T10:31:00", "todo_count": 3}
]
```

---

### POST /api/tags

创建标签。

**请求体**：

```json
{
  "name": "紧急",
  "color": "#dc3545"
}
```

**响应**：201 Created，返回 Tag 对象。

**错误**：400 — 名称/颜色格式无效；409 — 标签名已存在。

---

### GET /api/tags/:id

查询单个标签及其关联的所有待办事项。

**响应示例**：

```json
{
  "id": 1,
  "name": "紧急",
  "color": "#dc3545",
  "created_at": "2026-07-26T10:30:00",
  "todo_count": 2,
  "todos": [
    {"id": 1, "title": "完成周报", "completed": false, ...},
    {"id": 3, "title": "代码审查", "completed": true, ...}
  ]
}
```

---

### PUT /api/tags/:id

更新标签名称或颜色（部分更新）。

**请求体**：

```json
{
  "name": "高优",
  "color": "#ff6b6b"
}
```

**响应**：更新后的 Tag 对象。

**错误**：400 / 404 / 409（名称冲突）

---

### DELETE /api/tags/:id

删除标签（自动解除与所有待办的关联）。

**响应**：

```json
{"message": "标签已删除"}
```

---

## 5. 统计

### GET /api/stats

聚合统计数据（含热点端点统计）。

**响应示例**：

```json
{
  "hot_endpoints": {
    "list": 156,
    "create": 42,
    "detail": 38,
    "toggle": 25
  },
  "total_todos": 128,
  "completed_todos": 47,
  "overdue_count": 12,
  "by_category_priority": {
    "work": {"total": 45, "high": 20, "medium": 15, "low": 10},
    "personal": {"total": 30, "high": 5, "medium": 10, "low": 15},
    "study": {"total": 25, "high": 8, "medium": 12, "low": 5},
    "health": {"total": 18, "high": 3, "medium": 8, "low": 7},
    "other": {"total": 10, "high": 2, "medium": 5, "low": 3}
  },
  "by_completion": {
    "completed": 47,
    "pending": 81
  },
  "redis_available": true
}
```

---

### GET /api/stats/dashboard

仪表盘多维统计（7 天趋势 + 优先级/分类分布 + Top 标签）。

**响应示例**：

```json
{
  "daily_created": [
    {"day": "2026-07-20", "count": 12},
    {"day": "2026-07-21", "count": 8}
  ],
  "priority_distribution": [
    {"priority": "high", "total": 38, "completed_cnt": 20, "completion_rate": 52.6},
    {"priority": "medium", "total": 50, "completed_cnt": 18, "completion_rate": 36.0},
    {"priority": "low", "total": 40, "completed_cnt": 9, "completion_rate": 22.5}
  ],
  "category_stats": [
    {"category": "work", "total": 45, "completed_cnt": 20, "overdue_cnt": 5},
    {"category": "personal", "total": 30, "completed_cnt": 10, "overdue_cnt": 3}
  ],
  "top_tags": [
    {"name": "紧急", "color": "#dc3545", "usage_count": 25},
    {"name": "工作", "color": "#0d6efd", "usage_count": 18}
  ]
}
```

---

## 附录

### 端点速查表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 前端页面 |
| GET | `/health` | 健康检查 |
| GET | `/metrics` | Prometheus 指标 |
| GET | `/api/todos` | 待办列表（搜索/筛选/分页/排序） |
| POST | `/api/todos` | 创建待办 |
| GET | `/api/todos/:id` | 查询待办详情 |
| PUT | `/api/todos/:id` | 更新待办 |
| DELETE | `/api/todos/:id` | 删除待办 |
| POST | `/api/todos/:id/toggle` | 切换完成状态 |
| POST | `/api/todos/batch/delete-completed` | 批量删除已完成 |
| POST | `/api/todos/:id/tags` | 添加标签 |
| PUT | `/api/todos/:id/tags` | 覆盖设置标签 |
| DELETE | `/api/todos/:id/tags/:tag_id` | 移除标签 |
| GET | `/api/tags` | 标签列表 |
| POST | `/api/tags` | 创建标签 |
| GET | `/api/tags/:id` | 标签详情（含关联待办） |
| PUT | `/api/tags/:id` | 更新标签 |
| DELETE | `/api/tags/:id` | 删除标签 |
| GET | `/api/stats` | 聚合统计 |
| GET | `/api/stats/dashboard` | 仪表盘统计 |

**共 20 个端点**：9 GET / 6 POST / 3 PUT / 2 DELETE
