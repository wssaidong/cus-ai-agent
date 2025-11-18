# A2A RPC 快速参考

## 端点信息

| 项目 | 值 |
|------|-----|
| **协议** | JSON-RPC 2.0 |
| **端点** | `http://localhost:8000/api/v1/a2a` |
| **方法** | POST |
| **Content-Type** | application/json |

## 支持的方法

| 方法 | 说明 | 响应类型 |
|------|------|----------|
| `message/send` | 发送消息(同步) | Message |
| `message/stream` | 发送消息(流式) | SSE Stream |
| `tasks/get` | 获取任务状态 | Task |
| `tasks/cancel` | 取消任务 | Task |

## 请求格式

### 基础结构

```json
{
  "jsonrpc": "2.0",
  "method": "方法名",
  "id": 请求ID,
  "params": { /* 参数 */ }
}
```

### message/send

```json
{
  "jsonrpc": "2.0",
  "method": "message/send",
  "id": 1,
  "params": {
    "message": {
      "role": "user",
      "parts": [{"text": "消息内容"}],
      "messageId": "msg-001",
      "contextId": "session-001"
    }
  }
}
```

### message/stream

```json
{
  "jsonrpc": "2.0",
  "method": "message/stream",
  "id": 2,
  "params": {
    "message": {
      "role": "user",
      "parts": [{"text": "消息内容"}],
      "messageId": "msg-002",
      "contextId": "session-002"
    }
  }
}
```

### tasks/get

```json
{
  "jsonrpc": "2.0",
  "method": "tasks/get",
  "id": 3,
  "params": {
    "id": "task-123"
  }
}
```

### tasks/cancel

```json
{
  "jsonrpc": "2.0",
  "method": "tasks/cancel",
  "id": 4,
  "params": {
    "id": "task-123"
  }
}
```

## 响应格式

### 成功响应

```json
{
  "id": 1,
  "jsonrpc": "2.0",
  "result": { /* 结果数据 */ }
}
```

### 错误响应

```json
{
  "id": 1,
  "jsonrpc": "2.0",
  "error": {
    "code": -32600,
    "message": "错误描述"
  }
}
```

## 数据类型

### Message

```typescript
{
  role: "user" | "agent",
  parts: Part[],
  messageId: string,
  contextId: string,
  metadata?: object
}
```

### Part

```typescript
{
  kind: "text",
  text: string
}
```

### Task

```typescript
{
  id: string,
  contextId: string,
  status: {
    state: "pending" | "working" | "completed" | "failed" | "canceled"
  }
}
```

## 错误码

| 错误码 | 说明 |
|--------|------|
| -32700 | Parse error |
| -32600 | Invalid Request |
| -32601 | Method not found |
| -32602 | Invalid params |
| -32603 | Internal error |

## cURL 快速命令

### 发送消息

```bash
curl -X POST http://localhost:8000/api/v1/a2a \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"message/send","id":1,"params":{"message":{"role":"user","parts":[{"text":"你好"}],"messageId":"msg-001","contextId":"session-001"}}}'
```

### 流式消息

```bash
curl -X POST http://localhost:8000/api/v1/a2a \
  -H "Content-Type: application/json" \
  -N \
  -d '{"jsonrpc":"2.0","method":"message/stream","id":2,"params":{"message":{"role":"user","parts":[{"text":"写诗"}],"messageId":"msg-002","contextId":"session-002"}}}'
```

### 获取任务

```bash
curl -X POST http://localhost:8000/api/v1/a2a \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tasks/get","id":3,"params":{"id":"task-123"}}'
```

### 取消任务

```bash
curl -X POST http://localhost:8000/api/v1/a2a \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tasks/cancel","id":4,"params":{"id":"task-123"}}'
```

## Python 快速代码

### 同步发送

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/a2a",
    json={
        "jsonrpc": "2.0",
        "method": "message/send",
        "id": 1,
        "params": {
            "message": {
                "role": "user",
                "parts": [{"text": "你好"}],
                "messageId": "msg-001",
                "contextId": "session-001"
            }
        }
    }
)

result = response.json()["result"]
print(result["parts"][0]["text"])
```

### 异步发送

```python
import aiohttp
import asyncio

async def send_message():
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8000/api/v1/a2a",
            json={
                "jsonrpc": "2.0",
                "method": "message/send",
                "id": 1,
                "params": {
                    "message": {
                        "role": "user",
                        "parts": [{"text": "你好"}],
                        "messageId": "msg-001",
                        "contextId": "session-001"
                    }
                }
            }
        ) as response:
            result = await response.json()
            print(result["result"]["parts"][0]["text"])

asyncio.run(send_message())
```

## JavaScript 快速代码

### Fetch API

```javascript
fetch('http://localhost:8000/api/v1/a2a', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    jsonrpc: '2.0',
    method: 'message/send',
    id: 1,
    params: {
      message: {
        role: 'user',
        parts: [{ text: '你好' }],
        messageId: 'msg-001',
        contextId: 'session-001'
      }
    }
  })
})
.then(res => res.json())
.then(data => console.log(data.result.parts[0].text));
```

### Axios

```javascript
const axios = require('axios');

axios.post('http://localhost:8000/api/v1/a2a', {
  jsonrpc: '2.0',
  method: 'message/send',
  id: 1,
  params: {
    message: {
      role: 'user',
      parts: [{ text: '你好' }],
      messageId: 'msg-001',
      contextId: 'session-001'
    }
  }
})
.then(res => console.log(res.data.result.parts[0].text));
```

## 智能体能力

| 智能体 | 功能 | 触发关键词 |
|--------|------|-----------|
| **Search Agent** | 知识库搜索 | "搜索", "查找", "检索" |
| **Write Agent** | 知识库写入 | "添加", "保存", "写入" |
| **Analysis Agent** | 数据分析 | "分析", "计算", "推理" |
| **Execution Agent** | 工具执行 | "查询日志", "发送消息", "测试网络" |
| **Quality Agent** | 质量评估 | "评估", "质量", "优化" |

## 可用工具

| 工具 | 说明 |
|------|------|
| `search` | Elasticsearch 日志查询 |
| `发送群消息` | 美信群消息发送 |
| `网络质量查询` | 网络连通性测试 |
| `gw-api-count` | API 网关数据查询 |

## 最佳实践

### ✅ 推荐

- 使用唯一的 `contextId` 保持会话
- 使用唯一的 `messageId` 标识消息
- 实现错误重试机制
- 使用流式响应处理长文本
- 合理设置超时时间

### ❌ 避免

- 重复使用相同的 `messageId`
- 在不同会话中使用相同的 `contextId`
- 忽略错误处理
- 同步等待长时间任务
- 频繁创建新连接

## 常见问题

**Q: 如何保持对话上下文?**
A: 使用相同的 `contextId` 发送多条消息。

**Q: 如何处理长时间任务?**
A: 使用流式响应 (`message/stream`) 或任务管理 API。

**Q: 如何调用特定工具?**
A: 在消息中明确说明任务,系统会自动路由。

**Q: 支持并发请求吗?**
A: 支持,每个请求使用不同的 `id` 和 `contextId`。
