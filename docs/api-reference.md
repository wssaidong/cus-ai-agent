# API 参考文档

本文档提供完整的 API 接口参考。

## 📋 目录

- [基础信息](#基础信息)
- [认证](#认证)
- [对话接口](#对话接口)
- [知识库接口](#知识库接口)
- [OpenAI 兼容接口](#openai-兼容接口)
- [错误处理](#错误处理)

## 基础信息

### Base URL

```
http://localhost:8000
```

### 内容类型

所有请求和响应使用 JSON 格式：

```
Content-Type: application/json
```

### 版本

当前 API 版本：`v1`

## 认证

当前版本暂不需要认证。未来版本可能会添加 API Key 认证。

## 对话接口

### 1. 健康检查

检查服务状态。

**请求**

```http
GET /api/v1/health
```

**响应**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-10-02T12:00:00"
}
```

### 2. 普通对话

发送消息并获取智能体响应。

**请求**

```http
POST /api/v1/chat
Content-Type: application/json

{
  "message": "帮我计算 123 + 456",
  "session_id": "user-123",
  "config": {
    "temperature": 0.7,
    "max_tokens": 2000
  }
}
```

**参数说明**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| message | string | 是 | 用户消息 |
| session_id | string | 否 | 会话 ID，用于多轮对话 |
| config | object | 否 | 配置参数 |
| config.temperature | float | 否 | 温度参数 (0-1) |
| config.max_tokens | integer | 否 | 最大 token 数 |

**响应**

```json
{
  "response": "计算结果是 579",
  "session_id": "user-123",
  "metadata": {
    "execution_time": 1.23,
    "llm_calls": 1,
    "tool_calls": 1
  }
}
```

**响应字段**

| 字段 | 类型 | 说明 |
|------|------|------|
| response | string | 智能体响应 |
| session_id | string | 会话 ID |
| metadata | object | 元数据 |
| metadata.execution_time | float | 执行时间（秒） |
| metadata.llm_calls | integer | LLM 调用次数 |
| metadata.tool_calls | integer | 工具调用次数 |

### 3. 流式对话

使用 Server-Sent Events (SSE) 流式返回响应。

**请求**

```http
POST /api/v1/chat/stream
Content-Type: application/json

{
  "message": "讲一个故事",
  "session_id": "user-123"
}
```

**响应**

```
data: {"type": "start", "session_id": "user-123"}

data: {"type": "token", "content": "从前"}

data: {"type": "token", "content": "有"}

data: {"type": "token", "content": "一个"}

data: {"type": "end", "execution_time": 2.5}
```

**事件类型**

| 类型 | 说明 |
|------|------|
| start | 开始生成 |
| token | 生成的 token |
| end | 生成结束 |
| error | 发生错误 |

## 知识库接口

### 1. 上传文档

上传文档到知识库。

**请求**

```http
POST /api/v1/knowledge/upload
Content-Type: multipart/form-data

file: document.pdf
collection_name: my_knowledge
metadata: {"source": "manual"}
```

**参数说明**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| file | file | 是 | 文档文件 |
| collection_name | string | 否 | 集合名称 |
| metadata | string | 否 | JSON 格式的元数据 |

**支持的文件格式**

- `.txt` - 文本文件
- `.md` - Markdown 文件
- `.pdf` - PDF 文档
- `.docx` - Word 文档

**响应**

```json
{
  "success": true,
  "message": "成功上传文档",
  "document_ids": ["doc_123", "doc_124"],
  "collection_name": "my_knowledge"
}
```

### 2. 添加文本

直接添加文本到知识库。

**请求**

```http
POST /api/v1/knowledge/add-text
Content-Type: application/json

{
  "text": "这是要添加的文本内容",
  "collection_name": "my_knowledge",
  "metadata": {
    "source": "manual",
    "category": "faq"
  }
}
```

**响应**

```json
{
  "success": true,
  "message": "成功添加文本到知识库",
  "document_ids": ["doc_125"]
}
```

### 3. 搜索知识库

在知识库中搜索相关内容。

**请求**

```http
POST /api/v1/knowledge/search
Content-Type: application/json

{
  "query": "如何使用 API",
  "collection_name": "my_knowledge",
  "top_k": 5
}
```

**参数说明**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| query | string | 是 | 搜索查询 |
| collection_name | string | 否 | 集合名称 |
| top_k | integer | 否 | 返回结果数量 |

**响应**

```json
{
  "success": true,
  "results": [
    {
      "content": "API 使用方法...",
      "score": 0.95,
      "metadata": {
        "source": "manual.pdf",
        "page": 5
      }
    }
  ],
  "total": 1
}
```

### 4. 获取统计信息

获取知识库统计信息。

**请求**

```http
GET /api/v1/knowledge/stats
```

**响应**

```json
{
  "success": true,
  "stats": {
    "total_documents": 150,
    "total_chunks": 1200,
    "collections": ["default", "my_knowledge"]
  }
}
```

### 5. 清空知识库

清空指定集合的所有文档。

**请求**

```http
DELETE /api/v1/knowledge/clear?collection_name=my_knowledge
```

**响应**

```json
{
  "success": true,
  "message": "知识库已清空"
}
```

## OpenAI 兼容接口

### Chat Completions

兼容 OpenAI Chat Completions API。

**请求**

```http
POST /api/v1/completions
Content-Type: application/json

{
  "model": "gpt-4",
  "messages": [
    {"role": "system", "content": "你是一个助手"},
    {"role": "user", "content": "你好"}
  ],
  "temperature": 0.7,
  "max_tokens": 2000,
  "stream": false
}
```

**参数说明**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| model | string | 是 | 模型名称 |
| messages | array | 是 | 消息列表 |
| temperature | float | 否 | 温度参数 |
| max_tokens | integer | 否 | 最大 token 数 |
| stream | boolean | 否 | 是否流式输出 |

**响应（非流式）**

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-4",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "你好！有什么可以帮助你的吗？"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 15,
    "total_tokens": 35
  }
}
```

**响应（流式）**

```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-4","choices":[{"index":0,"delta":{"role":"assistant","content":"你"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-4","choices":[{"index":0,"delta":{"content":"好"},"finish_reason":null}]}

data: [DONE]
```

## 错误处理

### 错误响应格式

```json
{
  "error": "Error Type",
  "detail": "详细错误信息"
}
```

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

### 常见错误

#### 1. 参数验证错误

```json
{
  "error": "Validation Error",
  "detail": [
    {
      "loc": ["body", "message"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

#### 2. 服务错误

```json
{
  "error": "Internal Server Error",
  "detail": "LLM API 调用失败"
}
```

## 速率限制

当前版本暂无速率限制。未来版本可能会添加。

## 示例代码

### Python

```python
import requests

# 普通对话
response = requests.post(
    "http://localhost:8000/api/v1/chat",
    json={
        "message": "你好",
        "session_id": "test"
    }
)
print(response.json())

# 流式对话
response = requests.post(
    "http://localhost:8000/api/v1/chat/stream",
    json={"message": "讲个故事"},
    stream=True
)
for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
```

### JavaScript

```javascript
// 普通对话
fetch('http://localhost:8000/api/v1/chat', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    message: '你好',
    session_id: 'test'
  })
})
.then(res => res.json())
.then(data => console.log(data));

// 流式对话
const eventSource = new EventSource(
  'http://localhost:8000/api/v1/chat/stream'
);
eventSource.onmessage = (event) => {
  console.log(JSON.parse(event.data));
};
```

### cURL

```bash
# 普通对话
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "session_id": "test"}'

# 上传文档
curl -X POST "http://localhost:8000/api/v1/knowledge/upload" \
  -F "file=@document.pdf" \
  -F "collection_name=my_knowledge"
```

## 相关文档

- [快速开始](quickstart.md)
- [使用示例](usage_examples.md)
- [开发指南](development-guide.md)

---

如有问题，请查看 [故障排查指南](troubleshooting.md) 或提交 [Issue](https://github.com/wssaidong/cus-ai-agent/issues)。

