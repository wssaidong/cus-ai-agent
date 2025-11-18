# A2A RPC 使用文档

## 概述

本项目使用 [a2a-python SDK](https://github.com/a2aproject/a2a-python) 实现了完整的 Agent-to-Agent (A2A) 协议支持,提供基于 JSON-RPC 2.0 的智能体通信接口。

## 快速开始

### 1. 启动服务

```bash
# 使用启动脚本
bash scripts/start.sh

# 或直接运行
python run.py
```

服务启动后,A2A JSON-RPC API 将在以下端点可用:
- **端点**: `http://localhost:8000/api/v1/a2a`
- **协议**: JSON-RPC 2.0
- **传输**: HTTP POST

### 2. 基本请求格式

所有请求都遵循 JSON-RPC 2.0 规范:

```json
{
  "jsonrpc": "2.0",
  "method": "方法名",
  "id": 请求ID,
  "params": {
    // 方法参数
  }
}
```

## 支持的方法

### 1. message/send - 发送消息(同步)

发送消息到智能体并等待完整响应。

**请求示例**:

```bash
curl -X POST http://localhost:8000/api/v1/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "id": 1,
    "params": {
      "message": {
        "role": "user",
        "parts": [{"text": "你好,介绍一下自己"}],
        "messageId": "msg-001",
        "contextId": "session-001"
      }
    }
  }'
```

**响应示例**:

```json
{
  "id": 1,
  "jsonrpc": "2.0",
  "result": {
    "kind": "message",
    "role": "agent",
    "messageId": "msg-response-001",
    "contextId": "session-001",
    "parts": [
      {
        "kind": "text",
        "text": "你好！我是智能助手..."
      }
    ]
  }
}
```

### 2. message/stream - 发送消息(流式)

发送消息并以流式方式接收响应。

**请求示例**:

```bash
curl -X POST http://localhost:8000/api/v1/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/stream",
    "id": 2,
    "params": {
      "message": {
        "role": "user",
        "parts": [{"text": "写一首诗"}],
        "messageId": "msg-002",
        "contextId": "session-002"
      }
    }
  }'
```

**响应格式**: Server-Sent Events (SSE)

```
data: {"id":2,"jsonrpc":"2.0","result":{"contextId":"session-002","final":false,"kind":"status-update","status":{"message":{"contextId":"session-002","kind":"message","messageId":"...","parts":[{"kind":"text","text":"春"}],"role":"agent"},"state":"working"},"taskId":"..."}}

data: {"id":2,"jsonrpc":"2.0","result":{"contextId":"session-002","final":false,"kind":"status-update","status":{"message":{"contextId":"session-002","kind":"message","messageId":"...","parts":[{"kind":"text","text":"天"}],"role":"agent"},"state":"working"},"taskId":"..."}}

data: {"id":2,"jsonrpc":"2.0","result":{"contextId":"session-002","final":true,"kind":"status-update","status":{"message":{"contextId":"session-002","kind":"message","messageId":"...","parts":[{"kind":"text","text":"春天来了..."}],"role":"agent"},"state":"completed"},"taskId":"..."}}
```

**说明**:
- 每个流式事件都是一个完整的 JSON-RPC 响应
- `final: false` 表示中间状态,包含单个 token
- `final: true` 表示最终状态,包含完整响应
- `state: "working"` 表示处理中,`state: "completed"` 表示完成

### 3. tasks/get - 获取任务状态

查询任务的当前状态。

**请求示例**:

```bash
curl -X POST http://localhost:8000/api/v1/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/get",
    "id": 3,
    "params": {
      "id": "task-123"
    }
  }'
```

**响应示例**:

```json
{
  "id": 3,
  "jsonrpc": "2.0",
  "result": {
    "id": "task-123",
    "contextId": "session-001",
    "status": {
      "state": "completed"
    }
  }
}
```

### 4. tasks/cancel - 取消任务

取消正在执行的任务。

**请求示例**:

```bash
curl -X POST http://localhost:8000/api/v1/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/cancel",
    "id": 4,
    "params": {
      "id": "task-123"
    }
  }'
```

**响应示例**:

```json
{
  "id": 4,
  "jsonrpc": "2.0",
  "result": {
    "id": "task-123",
    "contextId": "session-001",
    "status": {
      "state": "canceled"
    }
  }
}
```

## 消息结构

### Message 对象

```typescript
{
  "role": "user" | "agent",           // 消息角色
  "parts": Part[],                     // 消息内容部分
  "messageId": string,                 // 消息唯一ID
  "contextId": string,                 // 会话上下文ID
  "metadata"?: object                  // 可选元数据
}
```

### Part 对象

目前支持文本类型:

```typescript
{
  "kind": "text",
  "text": string
}
```

### Task 对象

```typescript
{
  "id": string,                        // 任务ID
  "contextId": string,                 // 会话上下文ID
  "status": {
    "state": "pending" | "working" | "completed" | "failed" | "canceled"
  }
}
```

## 使用场景

### 场景 1: 简单问答

```bash
curl -X POST http://localhost:8000/api/v1/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "id": 1,
    "params": {
      "message": {
        "role": "user",
        "parts": [{"text": "什么是 A2A 协议?"}],
        "messageId": "msg-qa-001",
        "contextId": "qa-session"
      }
    }
  }'
```

### 场景 2: 知识库检索

```bash
curl -X POST http://localhost:8000/api/v1/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "id": 2,
    "params": {
      "message": {
        "role": "user",
        "parts": [{"text": "搜索关于 LangGraph 的文档"}],
        "messageId": "msg-search-001",
        "contextId": "search-session"
      }
    }
  }'
```

### 场景 3: 工具调用

```bash
curl -X POST http://localhost:8000/api/v1/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "id": 3,
    "params": {
      "message": {
        "role": "user",
        "parts": [{"text": "查询 API 网关的日志"}],
        "messageId": "msg-tool-001",
        "contextId": "tool-session"
      }
    }
  }'
```

## 错误处理

### 错误响应格式

```json
{
  "id": 1,
  "jsonrpc": "2.0",
  "error": {
    "code": -32600,
    "message": "Invalid Request"
  }
}
```

### 常见错误码

| 错误码 | 说明 |
|--------|------|
| -32700 | Parse error - JSON 解析错误 |
| -32600 | Invalid Request - 无效请求 |
| -32601 | Method not found - 方法不存在 |
| -32602 | Invalid params - 参数无效 |
| -32603 | Internal error - 内部错误 |

## 智能体能力

本智能体支持以下能力:

### 1. 智能对话
- 多轮对话
- 上下文理解
- 意图识别

### 2. 知识库检索
- 向量搜索
- 语义匹配
- 相关性排序

### 3. 工具调用
- Elasticsearch 日志查询
- 美信群消息发送
- 网络连通性测试
- 数据库查询

### 4. 多智能体协作
- Search Agent: 知识库搜索
- Write Agent: 知识库写入
- Analysis Agent: 数据分析
- Execution Agent: 工具执行
- Quality Agent: 质量评估

## 最佳实践

### 1. 使用唯一的 contextId

为每个会话使用唯一的 `contextId`,以保持对话上下文:

```javascript
const contextId = `session-${Date.now()}-${Math.random()}`;
```

### 2. 使用唯一的 messageId

为每条消息生成唯一的 `messageId`:

```javascript
const messageId = `msg-${Date.now()}-${Math.random()}`;
```

### 3. 处理流式响应

使用 SSE 客户端处理流式响应:

```javascript
const eventSource = new EventSource('/api/v1/a2a/stream');
eventSource.addEventListener('message', (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
});
```

### 4. 错误重试

实现指数退避重试机制:

```javascript
async function sendWithRetry(request, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fetch('/api/v1/a2a', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      });
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(r => setTimeout(r, Math.pow(2, i) * 1000));
    }
  }
}
```

## 技术架构

### 核心组件

1. **A2AFastAPIApplication**: a2a-sdk 提供的 FastAPI 应用
2. **A2ARequestHandler**: 实现 RequestHandler 接口的请求处理器
3. **LangGraph**: 多智能体编排引擎
4. **MCP Tools**: Model Context Protocol 工具集成

### 数据流

```
客户端请求
    ↓
JSON-RPC 解析 (a2a-sdk)
    ↓
A2ARequestHandler
    ↓
LangGraph 多智能体系统
    ↓
工具调用 / 知识库检索
    ↓
响应生成
    ↓
JSON-RPC 响应 (a2a-sdk)
    ↓
客户端接收
```

## 相关文档

- [A2A 协议规范](https://github.com/a2aproject/a2a-python)
- [JSON-RPC 2.0 规范](https://www.jsonrpc.org/specification)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [项目 API 文档](http://localhost:8000/docs)

## 常见问题

### Q: 如何保持会话上下文?

A: 使用相同的 `contextId` 发送多条消息,系统会自动维护会话历史。

### Q: 流式响应如何结束?

A: 当收到 `event: done` 事件时,表示流式响应结束。

### Q: 如何调用特定的智能体?

A: 在消息中明确说明任务类型,系统会自动路由到合适的智能体。例如:"搜索..." 会路由到 Search Agent。

### Q: 支持哪些消息格式?

A: 目前支持文本格式 (`text`),未来将支持图片、文件等多模态内容。

## 更新日志

### v1.0.0 (2025-11-18)
- ✅ 集成 a2a-sdk 官方实现
- ✅ 支持 message/send 和 message/stream
- ✅ 支持任务管理 (get/cancel)
- ✅ 集成 LangGraph 多智能体系统
- ✅ 集成 MCP 工具

