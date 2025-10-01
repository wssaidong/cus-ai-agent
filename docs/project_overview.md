# 项目总览

## 项目简介

**cus-ai-agent** 是一个基于LangGraph构建的智能体系统，通过FastAPI暴露OpenAPI接口，实现智能体编排功能。该项目支持工具调用、数据库访问、外部API调用和大模型推理，为开发者提供了一个完整的智能体解决方案。

## 核心特性

### 🤖 智能体编排
- 基于LangGraph的状态机管理
- 支持多轮对话和上下文管理
- 灵活的节点和边配置
- 可扩展的工具系统

### 🔧 工具集成
- **计算器工具**: 执行数学计算
- **文本处理工具**: 大小写转换、反转、长度计算
- **API调用工具**: 调用外部HTTP API
- **数据库工具**: 执行SQL查询（可选）
- **自定义工具**: 易于扩展的工具接口

### 🌐 API接口
- RESTful API设计
- OpenAPI/Swagger文档自动生成
- 支持普通和流式响应
- 完善的错误处理和验证

### 📊 可观测性
- 结构化日志记录
- 请求追踪和性能监控
- 健康检查接口
- 详细的元数据返回

### 🚀 部署友好
- Docker容器化支持
- 环境变量配置管理
- 生产环境部署方案
- 负载均衡和高可用支持

## 技术架构

### 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| Web框架 | FastAPI | 高性能异步Web框架 |
| 智能体框架 | LangGraph | 状态机编排框架 |
| LLM框架 | LangChain | 大模型应用开发框架 |
| 服务器 | Uvicorn | ASGI服务器 |
| 数据验证 | Pydantic | 数据模型和验证 |
| HTTP客户端 | httpx | 异步HTTP客户端 |
| 日志 | Loguru | 结构化日志 |

### 架构层次

```
┌─────────────────────────────────────┐
│         API层 (FastAPI)             │
│  - 路由处理                          │
│  - 请求验证                          │
│  - 响应格式化                        │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│      智能体层 (LangGraph)            │
│  - 状态管理                          │
│  - 节点编排                          │
│  - 工具调用                          │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│         工具层 (Tools)               │
│  - 数据库工具                        │
│  - API调用工具                       │
│  - 自定义工具                        │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│       模型层 (LLM Providers)         │
│  - OpenAI                           │
│  - 通义千问                          │
│  - 其他LLM                          │
└─────────────────────────────────────┘
```

## 项目结构

```
cus-ai-agent/
├── docs/                    # 📚 文档目录
│   ├── PRD.md              # 产品需求文档
│   ├── architecture.md     # 架构设计文档
│   ├── usage_examples.md   # 使用示例
│   ├── deployment.md       # 部署指南
│   ├── quickstart.md       # 快速开始
│   └── project_overview.md # 项目总览
│
├── scripts/                 # 🔧 脚本目录
│   ├── start.sh            # 启动脚本
│   └── test_api.sh         # API测试脚本
│
├── src/                     # 💻 源代码目录
│   ├── agent/              # 🤖 智能体核心
│   │   ├── graph.py        # LangGraph图定义
│   │   ├── nodes.py        # 节点定义
│   │   └── state.py        # 状态定义
│   │
│   ├── tools/              # 🛠️ 工具集
│   │   ├── database.py     # 数据库工具
│   │   ├── api_caller.py   # API调用工具
│   │   └── custom_tools.py # 自定义工具
│   │
│   ├── api/                # 🌐 API接口
│   │   ├── main.py         # FastAPI主入口
│   │   ├── routes.py       # 路由定义
│   │   └── models.py       # 数据模型
│   │
│   ├── config/             # ⚙️ 配置
│   │   └── settings.py     # 配置文件
│   │
│   └── utils/              # 🔨 工具类
│       └── logger.py       # 日志工具
│
├── tests/                   # 🧪 测试目录
│   ├── test_api.py         # API测试
│   └── test_tools.py       # 工具测试
│
├── logs/                    # 📝 日志目录
│
├── requirements.txt         # 📦 Python依赖
├── .env.example            # 🔐 环境变量示例
├── .gitignore              # 🚫 Git忽略文件
├── Dockerfile              # 🐳 Docker配置
├── docker-compose.yml      # 🐳 Docker Compose配置
└── README.md               # 📖 项目说明
```

## 核心模块说明

### 1. 智能体模块 (src/agent/)

负责智能体的核心逻辑和状态管理。

- **graph.py**: 定义LangGraph的状态图，包括节点、边和条件路由
- **nodes.py**: 实现各个节点的逻辑（入口、LLM、工具、输出）
- **state.py**: 定义智能体的状态结构

### 2. 工具模块 (src/tools/)

提供各种工具的实现。

- **database.py**: 数据库查询和操作工具
- **api_caller.py**: HTTP API调用工具
- **custom_tools.py**: 自定义工具（计算器、文本处理等）

### 3. API模块 (src/api/)

提供HTTP接口服务。

- **main.py**: FastAPI应用主入口，配置中间件和路由
- **routes.py**: API路由定义和处理逻辑
- **models.py**: Pydantic数据模型定义

### 4. 配置模块 (src/config/)

管理应用配置。

- **settings.py**: 使用Pydantic Settings管理环境变量和配置

### 5. 工具模块 (src/utils/)

提供通用工具函数。

- **logger.py**: 日志配置和管理

## 工作流程

### 请求处理流程

```
1. 用户发送HTTP请求
   ↓
2. FastAPI接收并验证请求
   ↓
3. 初始化智能体状态
   ↓
4. 进入LangGraph执行流程
   ├─ 入口节点：初始化
   ├─ LLM节点：调用大模型推理
   ├─ 决策节点：判断是否需要工具
   ├─ 工具节点：执行工具调用（如需要）
   └─ 输出节点：格式化结果
   ↓
5. 返回响应给用户
```

### LangGraph执行流程

```
┌──────────┐
│ 入口节点  │
└────┬─────┘
     ↓
┌──────────┐
│ LLM节点   │ ←─────┐
└────┬─────┘        │
     ↓              │
┌──────────┐        │
│ 决策节点  │        │
└────┬─────┘        │
     ↓              │
  需要工具？         │
   ↙    ↘          │
 是      否         │
 ↓       ↓         │
工具节点  输出节点   │
 │                 │
 └─────────────────┘
```

## API接口

### 主要接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | / | 根路径，返回服务信息 |
| GET | /api/v1/health | 健康检查 |
| POST | /api/v1/chat | 普通对话接口 |
| POST | /api/v1/chat/stream | 流式对话接口 |
| GET | /docs | OpenAPI文档 |
| GET | /openapi.json | OpenAPI规范 |

### 请求示例

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "帮我计算 123 + 456",
    "session_id": "user-001"
  }'
```

### 响应示例

```json
{
  "response": "计算结果是 579",
  "session_id": "user-001",
  "metadata": {
    "execution_time": 1.23,
    "llm_calls": 2,
    "tool_calls": 1
  }
}
```

## 配置说明

### 环境变量

主要配置项：

- `OPENAI_API_KEY`: OpenAI API密钥（必需）
- `MODEL_NAME`: 使用的模型名称
- `API_PORT`: API服务端口
- `LOG_LEVEL`: 日志级别
- `DATABASE_URL`: 数据库连接URL（可选）

### 工具开关

- `ENABLE_DATABASE_TOOL`: 启用数据库工具
- `ENABLE_API_TOOL`: 启用API调用工具
- `ENABLE_SEARCH_TOOL`: 启用搜索工具

## 扩展性

### 添加新工具

1. 在`src/tools/`创建新工具类
2. 继承`BaseTool`并实现`_run`方法
3. 在`src/tools/__init__.py`注册工具

### 自定义节点

1. 在`src/agent/nodes.py`添加新节点函数
2. 在`src/agent/graph.py`中添加到图中
3. 配置节点间的边和条件

### 集成新的LLM

1. 修改`src/agent/nodes.py`中的LLM初始化
2. 配置相应的API密钥和参数
3. 更新环境变量配置

## 性能指标

### 预期性能

- **响应时间**: < 2秒（不含LLM调用时间）
- **并发支持**: 100+ QPS（单实例）
- **可用性**: 99.9%+

### 优化建议

- 使用多进程部署（Gunicorn）
- 启用缓存机制
- 使用负载均衡
- 数据库连接池

## 安全性

### 安全措施

- API密钥通过环境变量管理
- 请求参数验证
- SQL注入防护
- 日志脱敏
- CORS配置

### 最佳实践

- 定期更新依赖
- 使用HTTPS
- 实现API限流
- 添加认证机制

## 文档资源

- [快速开始](quickstart.md) - 5分钟快速上手
- [使用示例](usage_examples.md) - 详细的使用示例
- [架构设计](architecture.md) - 系统架构详解
- [部署指南](deployment.md) - 生产环境部署
- [README](../README.md) - 项目说明

## 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证

MIT License

## 联系方式

- 项目仓库: <repository-url>
- 问题反馈: 提交Issue
- 邮件联系: <email>

---

**最后更新**: 2024-01-01
**版本**: 1.0.0

