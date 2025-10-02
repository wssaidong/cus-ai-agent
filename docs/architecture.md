# 架构设计文档

## 📋 项目简介

**cus-ai-agent** 是一个基于 LangGraph 构建的智能体系统,通过 FastAPI 暴露 RESTful API,实现智能体编排、工具调用、RAG 知识库检索和大模型推理。

### 核心特性

- 🤖 **智能体编排**: 基于 LangGraph 的状态机管理,支持多轮对话
- 🔧 **工具集成**: 计算器、文本处理、API 调用、数据库查询、RAG 检索
- 🌐 **OpenAI 兼容**: 支持 OpenAI API 格式,可直接替换使用
- 📊 **可观测性**: LangSmith 追踪、结构化日志、性能监控
- 🚀 **生产就绪**: Docker 部署、负载均衡、高可用支持

---

## 🛠️ 技术栈

| 层级 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **语言** | Python | 3.10+ | 主要开发语言 |
| **Web 框架** | FastAPI | 0.109+ | 高性能异步 Web 框架 |
| **智能体框架** | LangGraph | 0.2+ | 状态机编排框架 |
| **LLM 框架** | LangChain | 0.3+ | 大模型应用开发框架 |
| **服务器** | Uvicorn | 0.27+ | ASGI 服务器 |
| **数据验证** | Pydantic | 2.5+ | 数据模型和验证 |
| **向量数据库** | Milvus | 2.3+ | RAG 知识库 |
| **可观测性** | LangSmith | 0.1+ | 追踪和调试平台 |
| **HTTP 客户端** | httpx | 0.26+ | 异步 HTTP 客户端 |
| **日志** | Loguru | 0.7+ | 结构化日志 |

---

## 🏗️ 系统架构

### 3.1 整体架构

系统采用分层架构设计：

1. **API层**: FastAPI提供RESTful接口
2. **智能体层**: LangGraph编排智能体流程
3. **工具层**: 各类工具实现（数据库、API、自定义工具）
4. **模型层**: 大模型接口封装

### 3.2 LangGraph流程设计

智能体执行流程：

```
用户输入 → 入口节点 → LLM推理节点 → 决策节点
                              ↓
                         需要工具？
                         ↙      ↘
                      是          否
                      ↓           ↓
                  工具执行节点   输出节点
                      ↓
                  LLM推理节点（循环）
```

### 3.3 核心组件

#### 3.3.1 AgentState（状态管理）

```python
class AgentState(TypedDict):
    messages: List[BaseMessage]      # 消息历史
    tool_calls: List[ToolCall]       # 工具调用记录
    intermediate_steps: List[tuple]  # 中间步骤
    final_response: str              # 最终响应
    metadata: dict                   # 元数据
```

#### 3.3.2 节点类型

- **入口节点（Entry Node）**: 初始化状态，处理用户输入
- **LLM节点（LLM Node）**: 调用大模型进行推理和决策
- **工具节点（Tool Node）**: 执行具体工具调用
- **决策节点（Router Node）**: 判断下一步动作
- **输出节点（Output Node）**: 格式化并返回结果

#### 3.3.3 工具集

- **数据库工具**: 执行SQL查询、数据CRUD操作
- **API调用工具**: 调用外部HTTP API
- **搜索工具**: 网络搜索、知识库检索
- **自定义工具**: 业务特定工具

## 4. API接口设计

### 4.1 接口列表

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/v1/chat | 普通对话接口 |
| POST | /api/v1/chat/stream | 流式对话接口 |
| GET | /api/v1/health | 健康检查 |
| GET | /docs | OpenAPI文档 |
| GET | /openapi.json | OpenAPI规范 |

### 4.2 数据模型

#### 请求模型

```json
{
  "message": "用户消息内容",
  "session_id": "会话ID（可选）",
  "config": {
    "temperature": 0.7,
    "max_tokens": 2000,
    "tools_enabled": true
  }
}
```

#### 响应模型

```json
{
  "response": "智能体响应内容",
  "session_id": "会话ID",
  "metadata": {
    "tool_calls": [],
    "tokens_used": 150,
    "execution_time": 1.23
  }
}
```

## 5. 配置管理

使用环境变量和配置文件管理系统配置：

- `OPENAI_API_KEY`: OpenAI API密钥
- `MODEL_NAME`: 使用的模型名称
- `DATABASE_URL`: 数据库连接URL
- `LOG_LEVEL`: 日志级别
- `API_HOST`: API服务主机
- `API_PORT`: API服务端口

## 6. 安全性考虑

- API密钥通过环境变量管理
- 请求参数验证（Pydantic）
- 速率限制（可选）
- 日志脱敏
- CORS配置

## 7. 扩展性设计

- **工具插件化**: 易于添加新工具
- **模型适配器**: 支持多种LLM提供商
- **中间件支持**: 可添加认证、限流等中间件
- **异步处理**: 支持高并发请求

## 8. 监控和日志

- 结构化日志记录
- 请求追踪
- 性能指标收集
- 错误告警（可选）

## 9. 部署方案

- **开发环境**: 本地运行，使用uvicorn
- **生产环境**: Docker容器化部署
- **负载均衡**: Nginx反向代理
- **进程管理**: Supervisor或Systemd

## 10. 后续优化方向

- 添加会话管理和持久化
- 实现工具调用缓存
- 支持多轮对话上下文管理
- 添加用户认证和权限管理
- 实现分布式部署
- 添加监控和告警系统

