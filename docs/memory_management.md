# 记忆管理功能指南

## 概述

智能体现已集成 **InMemorySaver** 记忆功能，支持对话历史的持久化、会话隔离和状态恢复。

### 核心特性

- ✅ **内存中的状态保存** - 使用 LangGraph 的 InMemorySaver
- ✅ **会话隔离** - 每个会话独立管理记忆
- ✅ **检查点管理** - 记录执行过程中的状态快照
- ✅ **记忆查询** - 查看会话的完整记忆历史
- ✅ **记忆清空** - 支持单个或全量清空
- ✅ **记忆导出** - 导出会话数据用于分析

## 架构设计

```
┌─────────────────────────────────────────┐
│         FastAPI 应用                     │
├─────────────────────────────────────────┤
│  记忆管理 API 接口                       │
│  - /memory/sessions                     │
│  - /memory/sessions/{session_id}        │
│  - /memory/stats                        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      MemoryManager (记忆管理器)          │
│  - 会话管理                              │
│  - 检查点记录                            │
│  - 统计分析                              │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│    InMemorySaver (LangGraph)             │
│  - 状态持久化                            │
│  - 检查点存储                            │
└─────────────────────────────────────────┘
```

## 快速开始

### 1. 启用记忆功能

记忆功能默认启用。在 `src/agent/graph.py` 中：

```python
from src.agent.memory import get_memory_saver

# 创建图时自动集成 InMemorySaver
agent_graph = create_agent_graph(enable_memory=True)
```

### 2. 使用对话接口

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，请介绍一下自己",
    "session_id": "user_123_session_1"
  }'
```

**响应示例：**

```json
{
  "response": "你好！我是一个智能助手...",
  "session_id": "user_123_session_1",
  "metadata": {
    "execution_time": 2.34,
    "llm_calls": 1,
    "tool_calls": 0
  }
}
```

## API 接口

### 获取所有会话

```bash
GET /api/v1/memory/sessions
```

**响应：**

```json
{
  "status": "success",
  "data": [
    {
      "session_id": "session_1",
      "created_at": "2025-10-18T10:00:00",
      "updated_at": "2025-10-18T10:05:00",
      "message_count": 5,
      "checkpoint_count": 3,
      "metadata": {}
    }
  ],
  "count": 1
}
```

### 获取会话记忆

```bash
GET /api/v1/memory/sessions/{session_id}
```

**响应：**

```json
{
  "status": "success",
  "data": {
    "session_id": "session_1",
    "created_at": "2025-10-18T10:00:00",
    "updated_at": "2025-10-18T10:05:00",
    "message_count": 5,
    "checkpoint_count": 3,
    "checkpoints": [
      {
        "checkpoint_id": "cp_1",
        "timestamp": "2025-10-18T10:00:05",
        "state_keys": ["messages", "metadata"],
        "message_count": 1
      }
    ],
    "metadata": {}
  }
}
```

### 清空会话记忆

```bash
DELETE /api/v1/memory/sessions/{session_id}
```

**响应：**

```json
{
  "status": "success",
  "message": "已清空会话 session_1 的记忆"
}
```

### 清空所有记忆

```bash
DELETE /api/v1/memory/all
```

**响应：**

```json
{
  "status": "success",
  "message": "已清空所有记忆，共 5 个会话"
}
```

### 获取记忆统计

```bash
GET /api/v1/memory/stats
```

**响应：**

```json
{
  "status": "success",
  "data": {
    "total_sessions": 5,
    "total_messages": 25,
    "total_checkpoints": 15,
    "average_messages_per_session": 5.0,
    "average_checkpoints_per_session": 3.0
  }
}
```

### 导出会话记忆

```bash
GET /api/v1/memory/export/{session_id}
```

**响应：**

```json
{
  "status": "success",
  "data": {
    "session_id": "session_1",
    "created_at": "2025-10-18T10:00:00",
    "updated_at": "2025-10-18T10:05:00",
    "message_count": 5,
    "checkpoints": [...],
    "metadata": {}
  }
}
```

## 编程接口

### 获取记忆管理器

```python
from src.agent.memory import get_memory_manager

memory_manager = get_memory_manager()
```

### 创建会话

```python
session = memory_manager.create_session(
    session_id="user_123",
    metadata={"user_id": "123", "source": "web"}
)
```

### 记录检查点

```python
state = {
    "messages": [HumanMessage(content="你好")],
    "metadata": {"llm_calls": 1}
}

memory_manager.record_checkpoint(
    session_id="user_123",
    checkpoint_id="cp_1",
    state=state
)
```

### 获取会话记忆

```python
memory = memory_manager.get_session_memory("user_123")
print(f"消息数: {memory['message_count']}")
print(f"检查点数: {memory['checkpoint_count']}")
```

### 清空记忆

```python
# 清空单个会话
memory_manager.clear_session_memory("user_123")

# 清空所有记忆
memory_manager.clear_all_memory()
```

### 获取统计信息

```python
stats = memory_manager.get_memory_stats()
print(f"总会话数: {stats['total_sessions']}")
print(f"总消息数: {stats['total_messages']}")
```

## 最佳实践

### 1. 会话管理

```python
# 为每个用户创建唯一的会话ID
session_id = f"user_{user_id}_{timestamp}"

# 在对话请求中使用
response = await chat(ChatRequest(
    message="你好",
    session_id=session_id
))
```

### 2. 定期清理

```python
# 定期清理过期会话
import asyncio
from datetime import datetime, timedelta

async def cleanup_old_sessions():
    memory_manager = get_memory_manager()
    sessions = memory_manager.list_sessions()
    
    for session in sessions:
        created_at = datetime.fromisoformat(session["created_at"])
        if datetime.now() - created_at > timedelta(days=7):
            memory_manager.clear_session_memory(session["session_id"])
```

### 3. 监控记忆使用

```python
# 定期检查记忆统计
stats = memory_manager.get_memory_stats()

if stats["total_sessions"] > 1000:
    logger.warning("会话数过多，建议清理")

if stats["total_messages"] > 100000:
    logger.warning("消息数过多，建议清理")
```

## 故障排查

### 问题：记忆功能不工作

**解决方案：**

1. 检查 InMemorySaver 是否正确初始化
2. 确认 `enable_memory=True` 在图创建时设置
3. 查看日志中是否有错误信息

### 问题：会话数据丢失

**原因：** InMemorySaver 存储在内存中，应用重启后会丢失

**解决方案：** 
- 使用数据库持久化（如 PostgreSQL）
- 定期导出会话数据
- 实现自动备份机制

### 问题：内存占用过高

**解决方案：**

1. 定期清空过期会话
2. 限制每个会话的检查点数量
3. 考虑使用数据库存储

## 相关文档

- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [架构设计](architecture.md)
- [API 参考](api-reference.md)

