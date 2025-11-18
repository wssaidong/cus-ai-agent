# A2A 独立功能快速参考

## 概述

A2A (Agent-to-Agent) 功能现已独立于 Nacos 服务注册，使用独立的配置项。本文档提供快速参考。

## 配置

### 环境变量

```bash
# A2A AgentCard 配置
A2A_ENABLED=true                              # 是否启用 A2A 功能
A2A_SERVER_ADDRESSES=10.226.200.161:8848     # A2A 服务器地址（Nacos 服务器）
A2A_NAMESPACE=public                          # 命名空间
A2A_SERVICE_NAME=cus-ai-agent                # 服务名称
A2A_USERNAME=nacos                            # 认证用户名
A2A_PASSWORD=your_password                    # 认证密码

# A2A 服务 URL 配置（用于 AgentCard 注册）
# 方式1：直接指定完整 URL（优先级最高）
A2A_SERVICE_URL=http://192.168.1.100:8000/api/v1/a2a

# 方式2：分别指定 host 和 port（如果未设置 A2A_SERVICE_URL）
# A2A_SERVICE_HOST=192.168.1.100
# A2A_SERVICE_PORT=8000

# 如果以上都未设置，将使用 API_HOST 和 API_PORT
```

### Python 配置

```python
from src.config import settings

# 访问 A2A 配置
print(settings.a2a_enabled)           # True/False
print(settings.a2a_server_addresses)  # "10.226.200.161:8848"
print(settings.a2a_namespace)         # "public"
print(settings.a2a_service_name)      # "cus-ai-agent"
print(settings.a2a_username)          # "nacos"
print(settings.a2a_password)          # "your_password"

# 访问 A2A 服务 URL 配置
print(settings.a2a_service_url)       # "http://192.168.1.100:8000/api/v1/a2a" 或 None
print(settings.a2a_service_host)      # "192.168.1.100" 或 None
print(settings.a2a_service_port)      # 8000 或 None
```

## API 端点

### 基础 URL
```
http://localhost:8000/api/v1/a2a
```

### 端点列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/agent-cards` | 创建 AgentCard |
| GET | `/agent-cards/{agent_name}` | 获取 AgentCard 详情 |
| GET | `/agent-cards` | 列出 AgentCard |
| DELETE | `/agent-cards/{agent_name}` | 删除 AgentCard |
| GET | `/agent-cards/{agent_name}/versions` | 获取版本列表 |

## 使用示例

### 1. 创建 AgentCard

```bash
curl -X POST "http://localhost:8000/api/v1/a2a/agent-cards" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-agent",
    "description": "我的智能体",
    "version": "1.0.0",
    "url": "http://127.0.0.1:8000/api/v1/a2a",
    "skills": [
      {
        "id": "chat",
        "name": "对话",
        "description": "智能对话功能",
        "tags": ["chat", "conversation"],
        "inputModes": ["application/json"],
        "outputModes": ["application/json"]
      }
    ]
  }'
```

### 2. 获取 AgentCard

```bash
curl "http://localhost:8000/api/v1/a2a/agent-cards/my-agent"
```

### 3. 列出所有 AgentCard

```bash
curl "http://localhost:8000/api/v1/a2a/agent-cards?pageNo=1&pageSize=10"
```

### 4. 删除 AgentCard

```bash
curl -X DELETE "http://localhost:8000/api/v1/a2a/agent-cards/my-agent?version=1.0.0"
```

### 5. 获取版本列表

```bash
curl "http://localhost:8000/api/v1/a2a/agent-cards/my-agent/versions"
```

## Python SDK 使用

### 基础使用

```python
from src.utils.a2a_agent_card import AgentCardManager

# 创建管理器
manager = AgentCardManager(
    nacos_server="10.226.200.161:8848",
    namespace="public",
)

# 创建 AgentCard
success = manager.create_agent_card(
    name="my-agent",
    description="我的智能体",
    version="1.0.0",
    url="http://127.0.0.1:8000/api/v1/a2a",
    skills=[
        {
            "id": "chat",
            "name": "对话",
            "description": "智能对话功能",
            "tags": ["chat"],
            "inputModes": ["application/json"],
            "outputModes": ["application/json"],
        }
    ],
)

# 获取 AgentCard
card = manager.get_agent_card("my-agent")
print(card)

# 列出 AgentCard
cards = manager.list_agent_cards(page_no=1, page_size=10)
print(cards)

# 删除 AgentCard
success = manager.delete_agent_card("my-agent", "1.0.0")
```

### 自动注册

```python
import asyncio
from src.utils.a2a_auto_register import get_a2a_auto_register

async def main():
    # 获取自动注册管理器
    auto_register = get_a2a_auto_register()
    
    # 初始化
    await auto_register.initialize()
    
    # 注册 AgentCard（使用默认配置）
    await auto_register.register_agent_card()
    
    # 自定义注册
    await auto_register.register_agent_card(
        name="custom-agent",
        description="自定义智能体",
        version="2.0.0",
        skills=[
            {
                "id": "custom-skill",
                "name": "自定义技能",
                "description": "这是一个自定义技能",
                "tags": ["custom"],
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
            }
        ],
    )
    
    # 注销 AgentCard
    await auto_register.deregister_agent_card()

asyncio.run(main())
```

## 应用集成

### 启动时自动注册

应用启动时会自动注册 AgentCard（如果 `A2A_ENABLED=true`）：

```python
# 在 src/api/main.py 的 startup_event 中
@app.on_event("startup")
async def startup_event():
    # ... 其他启动逻辑 ...
    
    # 初始化并注册 A2A AgentCard
    try:
        a2a_register = get_a2a_auto_register()
        if await a2a_register.initialize():
            await a2a_register.register_agent_card()
    except Exception as e:
        app_logger.error(f"A2A AgentCard 注册失败: {str(e)}")
```

### 关闭时自动注销

应用关闭时会自动注销 AgentCard：

```python
# 在 src/api/main.py 的 shutdown_event 中
@app.on_event("shutdown")
async def shutdown_event():
    # 注销 A2A AgentCard
    try:
        a2a_register = get_a2a_auto_register()
        if a2a_register.registered:
            await a2a_register.deregister_agent_card()
        await a2a_register.close()
    except Exception as e:
        app_logger.error(f"A2A AgentCard 注销失败: {str(e)}")
```

## 常见问题

### 1. A2A 和 Nacos 的关系？

A2A 功能使用 Nacos 服务器作为注册中心，但不使用 Nacos 的服务注册与发现功能。A2A 只使用 Nacos 的 A2A API 端点来管理 AgentCard。

### 2. 如何禁用 A2A 功能？

设置环境变量：
```bash
A2A_ENABLED=false
```

### 3. Token 如何管理？

A2A 功能会自动管理访问令牌：
- 初始化时自动获取令牌
- 令牌过期前 5 分钟自动刷新
- 每次 API 调用前检查令牌有效性

### 4. 如何查看 A2A 日志？

A2A 相关日志会输出到应用日志中，包括：
- Token 获取成功/失败
- AgentCard 创建/删除成功/失败
- API 请求错误信息

### 5. 支持哪些认证方式？

目前支持 Token 认证（Bearer Token），使用 Nacos 的用户名和密码获取访问令牌。

## 技术细节

### Token 认证流程

1. 使用用户名和密码调用 `/nacos/v1/auth/login` 获取 Token
2. Token 有效期默认 5 小时（18000 秒）
3. 在 Token 过期前 5 分钟自动刷新
4. 所有 A2A API 请求使用 `Authorization: Bearer {token}` 头

### AgentCard 数据结构

```json
{
  "protocolVersion": "0.2.9",
  "name": "agent-name",
  "description": "Agent description",
  "version": "1.0.0",
  "preferredTransport": "JSONRPC",
  "capabilities": {
    "streaming": true,
    "pushNotifications": true,
    "stateTransitionHistory": false
  },
  "skills": [
    {
      "id": "skill-id",
      "name": "Skill Name",
      "description": "Skill description",
      "tags": ["tag1", "tag2"],
      "inputModes": ["application/json"],
      "outputModes": ["application/json"]
    }
  ],
  "defaultInputModes": ["application/json", "text/plain"],
  "defaultOutputModes": ["application/json"],
  "url": "http://127.0.0.1:8000/api/v1/a2a",
  "iconUrl": "http://example.com/icon.png",
  "provider": {
    "organization": "Your Organization",
    "url": "https://your-organization.com"
  }
}
```
