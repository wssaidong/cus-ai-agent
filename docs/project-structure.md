# 项目结构说明

本文档详细说明项目的目录结构和文件组织。

## 📁 目录树

```
cus-ai-agent/
├── .github/                    # GitHub 配置
│   ├── ISSUE_TEMPLATE/        # Issue 模板
│   │   ├── bug_report.md      # Bug 报告模板
│   │   └── feature_request.md # 功能请求模板
│   └── PULL_REQUEST_TEMPLATE.md # PR 模板
├── docs/                       # 文档目录
│   ├── README.md              # 文档索引
│   ├── quickstart.md          # 快速开始
│   ├── architecture.md        # 架构设计
│   ├── architecture-diagram.md # 架构图
│   ├── api-reference.md       # API 参考
│   ├── development-guide.md   # 开发指南
│   ├── deployment.md          # 部署指南
│   ├── usage_examples.md      # 使用示例
│   ├── troubleshooting.md     # 故障排查
│   ├── faq.md                 # 常见问题
│   ├── rag_milvus_integration.md # RAG 集成
│   └── langsmith_integration.md  # LangSmith 集成
├── scripts/                    # 脚本目录
│   ├── install.sh             # 安装脚本
│   ├── start.sh               # 启动脚本
│   ├── start_milvus.sh        # Milvus 启动脚本
│   └── test_api.sh            # API 测试脚本
├── src/                        # 源代码目录
│   ├── agent/                 # 智能体核心
│   │   ├── __init__.py
│   │   ├── graph.py           # LangGraph 图定义
│   │   ├── nodes.py           # 节点实现
│   │   └── state.py           # 状态定义
│   ├── api/                   # API 接口
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI 应用入口
│   │   ├── routes.py          # 对话路由
│   │   ├── knowledge_routes.py # 知识库路由
│   │   └── models.py          # 数据模型
│   ├── tools/                 # 工具集
│   │   ├── __init__.py        # 工具注册
│   │   ├── custom_tools.py    # 自定义工具
│   │   ├── database.py        # 数据库工具
│   │   ├── api_caller.py      # API 调用工具
│   │   ├── rag_tool.py        # RAG 工具
│   │   ├── document_loader.py # 文档加载器
│   │   └── mcp_adapter.py     # MCP 工具适配器（使用 langchain-mcp-adapters）
│   ├── config/                # 配置
│   │   ├── __init__.py
│   │   └── settings.py        # 配置管理
│   └── utils/                 # 工具类
│       ├── __init__.py
│       └── logger.py          # 日志工具
├── tests/                      # 测试目录
│   ├── __init__.py
│   ├── test_api.py            # API 测试
│   ├── test_tools.py          # 工具测试
│   └── test_completions.py    # Completions 测试
├── examples/                   # 示例代码
├── data/                       # 数据文件
├── logs/                       # 日志目录
├── volumes/                    # Docker 卷
│   ├── etcd/                  # Etcd 数据
│   ├── milvus/                # Milvus 数据
│   └── minio/                 # MinIO 数据
├── .env.example               # 环境变量示例
├── .gitignore                 # Git 忽略文件
├── .gitattributes             # Git 属性配置
├── .editorconfig              # 编辑器配置
├── CHANGELOG.md               # 变更日志
├── CODE_OF_CONDUCT.md         # 行为准则
├── CONTRIBUTING.md            # 贡献指南
├── Dockerfile                 # Docker 镜像
├── docker-compose.yml         # Docker Compose 配置
├── LICENSE                    # 许可证
├── README.md                  # 项目说明
├── requirements.txt           # Python 依赖
└── run.py                     # 启动脚本
```

## 📂 目录说明

### 根目录文件

| 文件 | 说明 |
|------|------|
| `.env.example` | 环境变量配置示例 |
| `.gitignore` | Git 忽略规则 |
| `.gitattributes` | Git 文件属性配置 |
| `.editorconfig` | 编辑器统一配置 |
| `CHANGELOG.md` | 版本变更记录 |
| `CODE_OF_CONDUCT.md` | 社区行为准则 |
| `CONTRIBUTING.md` | 贡献指南 |
| `Dockerfile` | Docker 镜像构建文件 |
| `docker-compose.yml` | Docker Compose 配置 |
| `LICENSE` | MIT 开源许可证 |
| `README.md` | 项目主文档 |
| `requirements.txt` | Python 依赖列表 |
| `run.py` | 服务启动脚本 |

### .github/ - GitHub 配置

存放 GitHub 相关的配置文件：

- **ISSUE_TEMPLATE/**: Issue 模板
  - `bug_report.md`: Bug 报告模板
  - `feature_request.md`: 功能请求模板
- **PULL_REQUEST_TEMPLATE.md**: PR 模板

### docs/ - 文档目录

存放所有项目文档：

| 文档 | 说明 |
|------|------|
| `README.md` | 文档索引和导航 |
| `quickstart.md` | 快速开始指南 |
| `architecture.md` | 系统架构设计 |
| `architecture-diagram.md` | 架构可视化图表 |
| `api-reference.md` | API 接口文档 |
| `development-guide.md` | 开发者指南 |
| `deployment.md` | 部署指南 |
| `usage_examples.md` | 使用示例 |
| `troubleshooting.md` | 故障排查 |
| `faq.md` | 常见问题 |
| `rag_milvus_integration.md` | RAG 集成指南 |
| `langsmith_integration.md` | LangSmith 集成 |

### scripts/ - 脚本目录

存放各种自动化脚本：

| 脚本 | 说明 |
|------|------|
| `install.sh` | 依赖安装脚本 |
| `start.sh` | 服务启动脚本 |
| `start_milvus.sh` | Milvus 启动脚本 |
| `test_api.sh` | API 测试脚本 |

### src/ - 源代码目录

#### src/agent/ - 智能体核心

智能体的核心逻辑：

| 文件 | 说明 |
|------|------|
| `graph.py` | LangGraph 图定义和编排 |
| `nodes.py` | 节点实现（入口、LLM、输出等） |
| `state.py` | 状态定义和类型 |

#### src/api/ - API 接口

FastAPI 应用和路由：

| 文件 | 说明 |
|------|------|
| `main.py` | FastAPI 应用入口 |
| `routes.py` | 对话相关路由 |
| `knowledge_routes.py` | 知识库相关路由 |
| `models.py` | Pydantic 数据模型 |

#### src/tools/ - 工具集

各种工具实现：

| 文件 | 说明 |
|------|------|
| `__init__.py` | 工具注册和管理 |
| `custom_tools.py` | 自定义工具（计算器、文本处理） |
| `database.py` | 数据库查询工具 |
| `api_caller.py` | HTTP API 调用工具 |
| `rag_tool.py` | RAG 知识库工具 |
| `document_loader.py` | 文档加载器 |
| `mcp_adapter.py` | MCP 工具适配器（使用 langchain-mcp-adapters） |

#### src/config/ - 配置

配置管理：

| 文件 | 说明 |
|------|------|
| `settings.py` | 配置类和环境变量加载 |

#### src/utils/ - 工具类

通用工具类：

| 文件 | 说明 |
|------|------|
| `logger.py` | 日志配置和管理 |

### tests/ - 测试目录

单元测试和集成测试：

| 文件 | 说明 |
|------|------|
| `test_api.py` | API 接口测试 |
| `test_tools.py` | 工具测试 |
| `test_completions.py` | Completions 接口测试 |

### examples/ - 示例代码

存放示例代码和演示脚本。

### data/ - 数据文件

存放数据文件，如知识库文档等。

### logs/ - 日志目录

存放应用日志文件，按日期分割。

### volumes/ - Docker 卷

Docker 容器的持久化数据：

- `etcd/`: Etcd 数据
- `milvus/`: Milvus 向量数据
- `minio/`: MinIO 对象存储

## 🔍 文件命名规范

### Python 文件

- 模块名：小写字母，下划线分隔（如 `custom_tools.py`）
- 类名：大驼峰命名（如 `CalculatorTool`）
- 函数名：小写字母，下划线分隔（如 `get_available_tools`）
- 常量：大写字母，下划线分隔（如 `MAX_TOKENS`）

### 文档文件

- 使用小写字母和连字符（如 `api-reference.md`）
- 或使用下划线（如 `usage_examples.md`）
- 保持一致性

### 配置文件

- `.env` 文件：大写字母，下划线分隔
- YAML/JSON：小写字母，下划线或连字符

## 📝 代码组织原则

### 1. 单一职责

每个模块、类、函数只负责一个功能。

### 2. 分层架构

- API 层：处理 HTTP 请求
- 业务层：智能体逻辑
- 工具层：具体功能实现
- 数据层：数据存储和访问

### 3. 依赖注入

通过配置和参数传递依赖，避免硬编码。

### 4. 可测试性

代码应该易于测试，避免全局状态。

## 🔧 扩展指南

### 添加新工具

1. 在 `src/tools/` 创建新文件
2. 实现工具类
3. 在 `src/tools/__init__.py` 注册
4. 添加测试

### 添加新 API

1. 在 `src/api/routes.py` 或创建新路由文件
2. 定义路由和处理函数
3. 在 `src/api/models.py` 定义数据模型
4. 在 `src/api/main.py` 注册路由
5. 更新 API 文档

### 添加新文档

1. 在 `docs/` 创建 Markdown 文件
2. 在 `docs/README.md` 添加链接
3. 更新主 `README.md`（如需要）

## 相关文档

- [开发指南](development-guide.md)
- [架构设计](architecture.md)
- [贡献指南](../CONTRIBUTING.md)

---

如有疑问，请查看 [FAQ](faq.md) 或提交 [Issue](https://github.com/wssaidong/cus-ai-agent/issues)。

