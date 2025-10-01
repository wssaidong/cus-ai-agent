# 智能体API服务

基于LangGraph构建的智能体系统，通过FastAPI暴露OpenAPI接口，实现智能体编排功能。

## 功能特性

- ✅ 基于LangGraph的智能体编排
- ✅ FastAPI提供RESTful API接口
- ✅ 支持工具调用（计算器、文本处理、API调用等）
- ✅ 支持数据库查询（可选）
- ✅ 支持流式输出（SSE）
- ✅ OpenAPI文档自动生成
- ✅ 结构化日志记录
- ✅ 配置化管理

## 技术栈

- **Python 3.10+**
- **LangGraph**: 智能体编排框架
- **LangChain**: LLM应用开发框架
- **FastAPI**: Web框架
- **Uvicorn**: ASGI服务器
- **OpenAI**: 大模型API

## 项目结构

```
cus-ai-agent/
├── docs/                    # 文档目录
│   ├── PRD.md              # 产品需求文档
│   └── architecture.md     # 架构设计文档
├── scripts/                 # 脚本目录
│   ├── start.sh            # 启动脚本
│   └── test_api.sh         # API测试脚本
├── src/                     # 源代码目录
│   ├── agent/              # 智能体核心
│   │   ├── graph.py        # LangGraph图定义
│   │   ├── nodes.py        # 节点定义
│   │   └── state.py        # 状态定义
│   ├── tools/              # 工具集
│   │   ├── database.py     # 数据库工具
│   │   ├── api_caller.py   # API调用工具
│   │   └── custom_tools.py # 自定义工具
│   ├── api/                # API接口
│   │   ├── main.py         # FastAPI主入口
│   │   ├── routes.py       # 路由定义
│   │   └── models.py       # 数据模型
│   ├── config/             # 配置
│   │   └── settings.py     # 配置文件
│   └── utils/              # 工具类
│       └── logger.py       # 日志工具
├── logs/                    # 日志目录
├── requirements.txt         # Python依赖
├── .env.example            # 环境变量示例
└── README.md               # 项目说明
```

## 快速开始

### 1. 环境准备

确保已安装Python 3.10或更高版本：

```bash
python3 --version
```

### 2. 克隆项目

```bash
git clone <repository-url>
cd cus-ai-agent
```

### 3. 配置环境变量

复制环境变量示例文件并编辑：

```bash
cp .env.example .env
```

编辑`.env`文件，配置必要的环境变量：

```env
# 必需配置
OPENAI_API_KEY=your_openai_api_key_here

# 可选配置
MODEL_NAME=gpt-4-turbo-preview
TEMPERATURE=0.7
API_PORT=8000
```

### 4. 安装依赖

#### 方式一：使用安装脚本（推荐）

```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

#### 方式二：手动安装

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 升级pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

### 5. 启动服务

#### 方式一：使用Python启动脚本（推荐）

```bash
# 确保已安装依赖
python run.py
```

#### 方式二：使用Shell脚本

```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

#### 方式三：直接运行

```bash
# 如果使用虚拟环境，先激活
source venv/bin/activate

# 启动服务
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. 访问服务

- **API文档**: http://localhost:8000/docs
- **ReDoc文档**: http://localhost:8000/redoc
- **OpenAPI规范**: http://localhost:8000/openapi.json

## API接口说明

### 1. 健康检查

```bash
GET /api/v1/health
```

### 2. 普通对话

```bash
POST /api/v1/chat
Content-Type: application/json

{
  "message": "帮我计算 123 + 456",
  "session_id": "user-123",
  "config": {
    "temperature": 0.7
  }
}
```

### 3. 流式对话

```bash
POST /api/v1/chat/stream
Content-Type: application/json

{
  "message": "你好",
  "session_id": "user-123"
}
```

## 使用示例

### Python示例

```python
import requests

# 普通对话
response = requests.post(
    "http://localhost:8000/api/v1/chat",
    json={
        "message": "帮我计算 123 + 456",
        "session_id": "test-session"
    }
)
print(response.json())
```

### cURL示例

```bash
# 普通对话
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "帮我计算 123 + 456",
    "session_id": "test-session"
  }'

# 健康检查
curl -X GET "http://localhost:8000/api/v1/health"
```

### 测试脚本

```bash
chmod +x scripts/test_api.sh
./scripts/test_api.sh
```

## 可用工具

### 1. 计算器工具（calculator）

执行数学计算：

```
用户: 帮我计算 123 + 456
智能体: 使用计算器工具计算结果为 579
```

### 2. 文本处理工具（text_process）

处理文本（大小写转换、反转、长度等）：

```
用户: 请把 hello world 转换为大写
智能体: 使用文本处理工具，结果为 HELLO WORLD
```

### 3. API调用工具（api_call）

调用外部HTTP API：

```
用户: 调用 https://api.example.com/data 获取数据
智能体: 使用API调用工具获取数据...
```

### 4. 数据库工具（database_query）

执行数据库查询（需要配置DATABASE_URL）：

```
用户: 查询用户表中的所有数据
智能体: 使用数据库工具执行查询...
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| OPENAI_API_KEY | OpenAI API密钥 | 必需 |
| MODEL_NAME | 模型名称 | gpt-4-turbo-preview |
| TEMPERATURE | 温度参数 | 0.7 |
| MAX_TOKENS | 最大令牌数 | 2000 |
| API_HOST | API主机 | 0.0.0.0 |
| API_PORT | API端口 | 8000 |
| LOG_LEVEL | 日志级别 | INFO |
| DATABASE_URL | 数据库URL | 可选 |

### 工具开关

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| ENABLE_DATABASE_TOOL | 启用数据库工具 | false |
| ENABLE_API_TOOL | 启用API调用工具 | true |
| ENABLE_SEARCH_TOOL | 启用搜索工具 | false |

## 开发指南

### 添加自定义工具

1. 在`src/tools/custom_tools.py`中创建新工具类：

```python
from langchain.tools import BaseTool

class MyCustomTool(BaseTool):
    name: str = "my_tool"
    description: str = "工具描述"
    
    def _run(self, query: str) -> str:
        # 实现工具逻辑
        return "结果"
```

2. 在`src/tools/__init__.py`中注册工具：

```python
from .custom_tools import MyCustomTool

def get_available_tools():
    tools = []
    tools.append(MyCustomTool())
    return tools
```

### 修改智能体流程

编辑`src/agent/graph.py`和`src/agent/nodes.py`来自定义智能体的执行流程。

## 部署

### Docker部署（待实现）

```bash
docker build -t cus-ai-agent .
docker run -p 8000:8000 --env-file .env cus-ai-agent
```

### 生产环境部署

使用Gunicorn + Uvicorn：

```bash
gunicorn src.api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

## 常见问题

### 1. 如何更换大模型？

修改`.env`文件中的`MODEL_NAME`和相关API配置。

### 2. 如何添加数据库支持？

1. 配置`DATABASE_URL`环境变量
2. 设置`ENABLE_DATABASE_TOOL=true`
3. 在`src/tools/database.py`中实现数据库连接逻辑

### 3. 如何启用流式输出？

使用`/api/v1/chat/stream`接口，返回Server-Sent Events流。

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 联系方式

如有问题，请提交Issue或联系维护者。

