# 开发指南

本文档为开发者提供详细的开发指导。

## 📋 目录

- [开发环境搭建](#开发环境搭建)
- [项目结构](#项目结构)
- [核心概念](#核心概念)
- [开发工作流](#开发工作流)
- [调试技巧](#调试技巧)
- [最佳实践](#最佳实践)

## 开发环境搭建

### 前置要求

- Python 3.10+
- Git
- VS Code 或 PyCharm（推荐）
- Docker（可选，用于本地测试）

### 环境配置

```bash
# 1. 克隆项目
git clone https://github.com/wssaidong/cus-ai-agent.git
cd cus-ai-agent

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装开发工具
pip install pytest pytest-cov black flake8 mypy pre-commit

# 5. 配置 pre-commit
pre-commit install

# 6. 配置环境变量
cp .env.example .env
# 编辑 .env 文件
```

### IDE 配置

#### VS Code

推荐安装以下插件：

- Python
- Pylance
- Python Test Explorer
- Mermaid Preview
- GitLens

配置文件 `.vscode/settings.json`:

```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "editor.formatOnSave": true,
  "editor.rulers": [100]
}
```

#### PyCharm

1. 设置 Python 解释器为虚拟环境
2. 启用 Black 格式化
3. 配置 Flake8 检查
4. 启用 pytest 测试框架

## 项目结构

```
cus-ai-agent/
├── src/                      # 源代码
│   ├── agent/               # 智能体核心
│   │   ├── graph.py        # LangGraph 图定义
│   │   ├── nodes.py        # 节点实现
│   │   └── state.py        # 状态定义
│   ├── api/                # API 接口
│   │   ├── main.py         # FastAPI 应用
│   │   ├── routes.py       # 路由处理
│   │   ├── knowledge_routes.py  # 知识库路由
│   │   └── models.py       # 数据模型
│   ├── tools/              # 工具集
│   │   ├── __init__.py     # 工具注册
│   │   ├── custom_tools.py # 自定义工具
│   │   ├── api_caller.py   # API 调用工具
│   │   ├── rag_tool.py     # RAG 工具
│   │   └── document_loader.py  # 文档加载器
│   ├── config/             # 配置
│   │   └── settings.py     # 配置管理
│   └── utils/              # 工具类
│       └── logger.py       # 日志工具
├── tests/                   # 测试
│   ├── test_api.py
│   ├── test_tools.py
│   └── test_completions.py
├── docs/                    # 文档
├── scripts/                 # 脚本
├── examples/                # 示例
└── data/                    # 数据文件
```

## 核心概念

### 1. LangGraph 智能体

LangGraph 是一个基于图的智能体编排框架：

```python
from langgraph.graph import StateGraph
from src.agent.state import AgentState
from src.agent.nodes import entry_node, llm_node, output_node

# 创建图
graph = StateGraph(AgentState)

# 添加节点
graph.add_node("entry", entry_node)
graph.add_node("llm", llm_node)
graph.add_node("output", output_node)

# 添加边
graph.add_edge("entry", "llm")
graph.add_edge("llm", "output")

# 编译
agent = graph.compile()
```

### 2. 工具系统

工具是智能体可以调用的功能模块：

```python
from langchain.tools import BaseTool

class MyTool(BaseTool):
    name: str = "my_tool"
    description: str = "工具描述"
    
    def _run(self, query: str) -> str:
        """同步执行"""
        return "结果"
    
    async def _arun(self, query: str) -> str:
        """异步执行"""
        return self._run(query)
```

### 3. 状态管理

状态在节点间传递：

```python
from typing import TypedDict, List
from langchain.schema import BaseMessage

class AgentState(TypedDict):
    messages: List[BaseMessage]
    final_response: str
    is_finished: bool
    metadata: dict
```

### 4. RAG 知识库

RAG（检索增强生成）流程：

1. 文档加载和分割
2. 生成 Embedding
3. 存储到向量数据库
4. 检索相关文档
5. 生成答案

## 开发工作流

### 1. 添加新工具

```python
# 1. 在 src/tools/custom_tools.py 中定义工具
class NewTool(BaseTool):
    name: str = "new_tool"
    description: str = "新工具的描述"
    
    def _run(self, query: str) -> str:
        # 实现逻辑
        return "结果"

# 2. 在 src/tools/__init__.py 中注册
def get_available_tools():
    tools = []
    tools.append(NewTool())
    return tools

# 3. 添加测试
def test_new_tool():
    tool = NewTool()
    result = tool._run("测试输入")
    assert result == "预期结果"
```

### 2. 添加新 API 端点

```python
# 在 src/api/routes.py 中添加
@router.post("/new-endpoint")
async def new_endpoint(request: NewRequest):
    """新端点描述"""
    try:
        # 处理逻辑
        return {"result": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 3. 修改智能体流程

```python
# 在 src/agent/nodes.py 中添加新节点
def new_node(state: AgentState) -> AgentState:
    """新节点"""
    # 处理逻辑
    return state

# 在 src/agent/graph.py 中添加到图
graph.add_node("new_node", new_node)
graph.add_edge("entry", "new_node")
```

## 调试技巧

### 1. 使用 LangSmith 追踪

```python
# 在 .env 中启用
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_key

# 查看追踪：https://smith.langchain.com/
```

### 2. 日志调试

```python
from src.utils import app_logger

# 添加日志
app_logger.info("信息日志")
app_logger.error("错误日志")
app_logger.debug("调试日志")
```

### 3. 断点调试

```python
# 使用 pdb
import pdb; pdb.set_trace()

# 或使用 IDE 断点
```

### 4. 单元测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_tools.py::test_calculator_tool

# 查看覆盖率
pytest --cov=src tests/
```

## 最佳实践

### 1. 代码风格

```python
# 使用类型注解
def process_data(data: List[str]) -> Dict[str, int]:
    """处理数据"""
    pass

# 使用文档字符串
def function_name(param: str) -> str:
    """
    函数描述
    
    Args:
        param: 参数描述
        
    Returns:
        返回值描述
    """
    pass

# 使用有意义的变量名
user_count = len(users)  # 好
n = len(users)  # 不好
```

### 2. 错误处理

```python
# 捕获具体异常
try:
    result = process_data(data)
except ValueError as e:
    app_logger.error(f"数据错误: {e}")
    raise
except Exception as e:
    app_logger.error(f"未知错误: {e}")
    raise
```

### 3. 配置管理

```python
# 使用配置类
from src.config import settings

# 不要硬编码
api_key = settings.openai_api_key  # 好
api_key = "sk-xxx"  # 不好
```

### 4. 测试编写

```python
# 测试应该独立、可重复
def test_calculator():
    tool = CalculatorTool()
    assert tool._run("2 + 2") == "4"
    assert tool._run("10 * 5") == "50"

# 使用 fixture
@pytest.fixture
def calculator_tool():
    return CalculatorTool()

def test_with_fixture(calculator_tool):
    assert calculator_tool._run("2 + 2") == "4"
```

### 5. 性能优化

```python
# 使用异步
async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

# 使用缓存
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_function(param):
    # 耗时操作
    pass
```

## 常用命令

```bash
# 代码格式化
black src/ tests/

# 代码检查
flake8 src/ tests/

# 类型检查
mypy src/

# 运行测试
pytest tests/

# 启动服务
python run.py

# 查看日志
tail -f logs/app_$(date +%Y-%m-%d).log
```

## 相关资源

- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [LangChain 文档](https://python.langchain.com/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Milvus 文档](https://milvus.io/docs)

## 获取帮助

- 查看 [文档](../README.md)
- 搜索 [Issues](https://github.com/wssaidong/cus-ai-agent/issues)
- 阅读 [贡献指南](../CONTRIBUTING.md)

---

祝你开发愉快！🚀

