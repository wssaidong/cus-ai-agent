# 使用示例

本文档提供了智能体API服务的详细使用示例。

## 目录

- [基础使用](#基础使用)
- [工具调用示例](#工具调用示例)
- [流式输出示例](#流式输出示例)
- [Python客户端示例](#python客户端示例)
- [JavaScript客户端示例](#javascript客户端示例)

## 基础使用

### 1. 健康检查

```bash
curl -X GET "http://localhost:8000/api/v1/health"
```

响应：
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T12:00:00"
}
```

### 2. 简单对话

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，请介绍一下你自己",
    "session_id": "user-001"
  }'
```

响应：
```json
{
  "response": "你好！我是一个智能助手...",
  "session_id": "user-001",
  "metadata": {
    "execution_time": 1.23,
    "llm_calls": 1,
    "tool_calls": 0
  }
}
```

## 工具调用示例

### 1. 计算器工具

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "帮我计算 (123 + 456) * 2",
    "session_id": "calc-001"
  }'
```

响应：
```json
{
  "response": "计算结果是 1158",
  "session_id": "calc-001",
  "metadata": {
    "execution_time": 2.15,
    "llm_calls": 2,
    "tool_calls": 1
  }
}
```

### 2. 文本处理工具

#### 转换为大写

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "请把 hello world 转换为大写",
    "session_id": "text-001"
  }'
```

#### 反转文本

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "请反转文本 hello",
    "session_id": "text-002"
  }'
```

#### 获取文本长度

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "hello world 有多少个字符？",
    "session_id": "text-003"
  }'
```

### 3. API调用工具

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "请调用 https://api.github.com/users/github 获取用户信息",
    "session_id": "api-001"
  }'
```

### 4. 组合使用多个工具

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "先计算 10 + 20，然后把结果转换为文本并反转",
    "session_id": "combo-001"
  }'
```

## 流式输出示例

### cURL示例

```bash
curl -X POST "http://localhost:8000/api/v1/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "请详细介绍一下人工智能",
    "session_id": "stream-001"
  }'
```

响应（Server-Sent Events）：
```
data: {'type': 'start', 'session_id': 'stream-001'}

data: {'type': 'token', 'content': '人工智能...'}

data: {'type': 'end', 'execution_time': 3.45}
```

## Python客户端示例

### 基础使用

```python
import requests

class AgentClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def chat(self, message, session_id=None, config=None):
        """发送聊天请求"""
        url = f"{self.base_url}/api/v1/chat"
        payload = {
            "message": message,
            "session_id": session_id,
            "config": config or {}
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    
    def health(self):
        """健康检查"""
        url = f"{self.base_url}/api/v1/health"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()


# 使用示例
client = AgentClient()

# 健康检查
health = client.health()
print(f"服务状态: {health['status']}")

# 简单对话
result = client.chat("你好", session_id="user-123")
print(f"响应: {result['response']}")

# 使用计算器
result = client.chat("计算 100 + 200", session_id="user-123")
print(f"计算结果: {result['response']}")

# 文本处理
result = client.chat("把 hello 转换为大写", session_id="user-123")
print(f"处理结果: {result['response']}")
```

### 流式输出

```python
import requests
import json

def chat_stream(message, session_id=None):
    """流式聊天"""
    url = "http://localhost:8000/api/v1/chat/stream"
    payload = {
        "message": message,
        "session_id": session_id
    }
    
    with requests.post(url, json=payload, stream=True) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                # 解析SSE数据
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]  # 移除 'data: ' 前缀
                    event = json.loads(data.replace("'", '"'))
                    
                    if event['type'] == 'start':
                        print(f"开始会话: {event['session_id']}")
                    elif event['type'] == 'token':
                        print(event['content'], end='', flush=True)
                    elif event['type'] == 'end':
                        print(f"\n执行时间: {event['execution_time']}秒")
                    elif event['type'] == 'error':
                        print(f"\n错误: {event['message']}")


# 使用示例
chat_stream("请详细介绍一下Python编程语言", session_id="stream-001")
```

### 异步客户端

```python
import asyncio
import httpx

class AsyncAgentClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    async def chat(self, message, session_id=None, config=None):
        """异步发送聊天请求"""
        url = f"{self.base_url}/api/v1/chat"
        payload = {
            "message": message,
            "session_id": session_id,
            "config": config or {}
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    
    async def batch_chat(self, messages):
        """批量发送聊天请求"""
        tasks = [self.chat(msg) for msg in messages]
        return await asyncio.gather(*tasks)


# 使用示例
async def main():
    client = AsyncAgentClient()
    
    # 单个请求
    result = await client.chat("你好")
    print(result['response'])
    
    # 批量请求
    messages = [
        "计算 10 + 20",
        "把 hello 转换为大写",
        "反转文本 world"
    ]
    results = await client.batch_chat(messages)
    for i, result in enumerate(results):
        print(f"请求 {i+1}: {result['response']}")

# 运行
asyncio.run(main())
```

## JavaScript客户端示例

### 基础使用

```javascript
class AgentClient {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  async chat(message, sessionId = null, config = {}) {
    const url = `${this.baseUrl}/api/v1/chat`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        config,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  async health() {
    const url = `${this.baseUrl}/api/v1/health`;
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }
}

// 使用示例
const client = new AgentClient();

// 健康检查
client.health().then(health => {
  console.log('服务状态:', health.status);
});

// 简单对话
client.chat('你好', 'user-123').then(result => {
  console.log('响应:', result.response);
});

// 使用计算器
client.chat('计算 100 + 200', 'user-123').then(result => {
  console.log('计算结果:', result.response);
});
```

### 流式输出

```javascript
async function chatStream(message, sessionId = null) {
  const url = 'http://localhost:8000/api/v1/chat/stream';
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      session_id: sessionId,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        const event = JSON.parse(data.replace(/'/g, '"'));

        if (event.type === 'start') {
          console.log('开始会话:', event.session_id);
        } else if (event.type === 'token') {
          process.stdout.write(event.content);
        } else if (event.type === 'end') {
          console.log('\n执行时间:', event.execution_time, '秒');
        } else if (event.type === 'error') {
          console.error('\n错误:', event.message);
        }
      }
    }
  }
}

// 使用示例
chatStream('请详细介绍一下JavaScript编程语言', 'stream-001');
```

## 配置参数示例

### 自定义温度和最大令牌数

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "写一首关于春天的诗",
    "session_id": "poem-001",
    "config": {
      "temperature": 0.9,
      "max_tokens": 500
    }
  }'
```

## 错误处理示例

### Python错误处理

```python
import requests

def safe_chat(message, session_id=None):
    """安全的聊天请求"""
    try:
        url = "http://localhost:8000/api/v1/chat"
        response = requests.post(
            url,
            json={"message": message, "session_id": session_id},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        print("请求超时")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"HTTP错误: {e}")
        return None
    except Exception as e:
        print(f"未知错误: {e}")
        return None


# 使用示例
result = safe_chat("你好")
if result:
    print(result['response'])
```

## 总结

本文档提供了智能体API服务的各种使用示例，包括：

- 基础API调用
- 各种工具的使用方法
- 流式输出的实现
- Python和JavaScript客户端示例
- 错误处理最佳实践

更多信息请参考[README.md](../README.md)和[架构设计文档](architecture.md)。

