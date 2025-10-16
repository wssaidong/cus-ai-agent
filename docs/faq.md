# 常见问题 (FAQ)

本文档回答常见问题。

## 📋 目录

- [通用问题](#通用问题)
- [功能问题](#功能问题)
- [配置问题](#配置问题)
- [部署问题](#部署问题)
- [开发问题](#开发问题)

## 通用问题

### Q: 这个项目是做什么的？

**A:** cus-ai-agent 是一个基于 LangGraph 的智能体系统，提供：
- 智能对话和任务执行
- 工具调用（计算器、API、数据库等）
- RAG 知识库检索
- OpenAI 兼容的 API 接口

### Q: 支持哪些大模型？

**A:** 支持所有兼容 OpenAI API 的模型：
- OpenAI: GPT-4, GPT-3.5-turbo
- Azure OpenAI
- 通义千问（DashScope）
- DeepSeek
- 其他兼容 OpenAI API 的模型

配置方法：
```bash
# 在 .env 中
OPENAI_API_KEY=your_key
OPENAI_API_BASE=https://api.openai.com/v1
MODEL_NAME=gpt-4
```

### Q: 需要什么环境？

**A:** 
- Python 3.10 或更高版本
- 4GB+ 内存
- 可选：Docker（用于 Milvus）

### Q: 是否免费？

**A:** 
- 项目代码：完全免费开源（MIT 许可证）
- 运行成本：需要支付 LLM API 调用费用

### Q: 如何获取 API Key？

**A:**
- OpenAI: https://platform.openai.com/api-keys
- 通义千问: https://dashscope.console.aliyun.com/
- LangSmith: https://smith.langchain.com/

## 功能问题

### Q: 如何添加自定义工具？

**A:** 

1. 创建工具类：
```python
# src/tools/custom_tools.py
from langchain.tools import BaseTool

class MyTool(BaseTool):
    name: str = "my_tool"
    description: str = "工具描述"
    
    def _run(self, query: str) -> str:
        # 实现逻辑
        return "结果"
```

2. 注册工具：
```python
# src/tools/__init__.py
def get_available_tools():
    tools = []
    tools.append(MyTool())
    return tools
```

详见 [开发指南](development-guide.md)。

### Q: 如何实现多轮对话？

**A:** 使用 `session_id` 参数：

```python
# 第一轮
response1 = requests.post(
    "http://localhost:8000/api/v1/chat",
    json={"message": "我叫张三", "session_id": "user-123"}
)

# 第二轮（使用相同的 session_id）
response2 = requests.post(
    "http://localhost:8000/api/v1/chat",
    json={"message": "我叫什么名字？", "session_id": "user-123"}
)
```

### Q: 如何使用 RAG 知识库？

**A:**

1. 启用 RAG：
```bash
# 在 .env 中
ENABLE_RAG_TOOL=true
```

2. 启动 Milvus：
```bash
./scripts/start_milvus.sh
```

3. 上传文档：
```bash
curl -X POST "http://localhost:8000/api/v1/knowledge/upload" \
  -F "file=@document.pdf"
```

4. 使用知识库：
```python
response = requests.post(
    "http://localhost:8000/api/v1/chat",
    json={"message": "根据文档回答：..."}
)
```

详见 [RAG 集成指南](rag_milvus_integration.md)。

### Q: 支持流式输出吗？

**A:** 支持。使用 `/api/v1/chat/stream` 接口：

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/chat/stream",
    json={"message": "讲个故事"},
    stream=True
)

for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
```

### Q: 如何调用外部 API？

**A:** 使用 API 调用工具：

```python
response = requests.post(
    "http://localhost:8000/api/v1/chat",
    json={
        "message": "调用 https://api.example.com/data 获取数据"
    }
)
```

或在 .env 中启用：
```bash
ENABLE_API_TOOL=true
```

## 配置问题

### Q: 如何更换模型？

**A:** 修改 .env 文件：

```bash
# 使用 GPT-4
MODEL_NAME=gpt-4

# 使用 GPT-3.5
MODEL_NAME=gpt-3.5-turbo

# 使用通义千问
MODEL_NAME=qwen-turbo
OPENAI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_API_KEY=your_dashscope_key
```

### Q: 如何优化成本？

**A:** 

1. 使用更便宜的模型：
```bash
# DeepSeek（$0.14/1M tokens）
MODEL_NAME=deepseek-chat
OPENAI_API_BASE=https://api.deepseek.com/v1
```

2. 对话和 Embedding 分离：
```bash
# 对话用 DeepSeek
OPENAI_API_KEY=sk-deepseek-xxx
MODEL_NAME=deepseek-chat

# Embedding 用 OpenAI
RAG_OPENAI_API_KEY=sk-openai-xxx
RAG_EMBEDDING_MODEL=text-embedding-3-small
```

3. 减少 token 使用：
```bash
MAX_TOKENS=1000
TEMPERATURE=0.5
```


### Q: 如何启用 LangSmith 追踪？

**A:**

```bash
# 在 .env 中
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=cus-ai-agent
```

访问 https://smith.langchain.com/ 查看追踪数据。

## 部署问题

### Q: 如何部署到生产环境？

**A:** 

1. 使用 Gunicorn + Uvicorn：
```bash
gunicorn src.api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

2. 使用 Docker：
```bash
docker build -t cus-ai-agent .
docker run -p 8000:8000 --env-file .env cus-ai-agent
```

3. 使用 Docker Compose：
```bash
docker-compose up -d
```

详见 [部署指南](deployment.md)。

### Q: 如何配置 HTTPS？

**A:** 使用 Nginx 反向代理：

```nginx
server {
    listen 443 ssl;
    server_name api.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Q: 如何实现负载均衡？

**A:** 

1. 启动多个实例：
```bash
# 实例 1
API_PORT=8001 python run.py &

# 实例 2
API_PORT=8002 python run.py &
```

2. 配置 Nginx：
```nginx
upstream backend {
    server localhost:8001;
    server localhost:8002;
}

server {
    location / {
        proxy_pass http://backend;
    }
}
```

### Q: 如何监控服务？

**A:**

1. 健康检查：
```bash
curl http://localhost:8000/api/v1/health
```

2. 使用 LangSmith 监控
3. 查看日志：
```bash
tail -f logs/app_*.log
```

4. 使用 Prometheus + Grafana（可选）

## 开发问题

### Q: 如何运行测试？

**A:**

```bash
# 安装测试依赖
pip install pytest pytest-cov

# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_tools.py

# 查看覆盖率
pytest --cov=src tests/
```

### Q: 如何贡献代码？

**A:**

1. Fork 项目
2. 创建分支：`git checkout -b feature/xxx`
3. 提交代码：`git commit -m "feat: xxx"`
4. 推送分支：`git push origin feature/xxx`
5. 创建 Pull Request

详见 [贡献指南](../CONTRIBUTING.md)。

### Q: 代码规范是什么？

**A:**

- 遵循 PEP 8
- 使用 Black 格式化
- 使用类型注解
- 添加文档字符串
- 编写单元测试

```bash
# 格式化代码
black src/ tests/

# 检查代码
flake8 src/ tests/

# 类型检查
mypy src/
```

### Q: 如何调试？

**A:**

1. 启用调试日志：
```bash
LOG_LEVEL=DEBUG
```

2. 使用 LangSmith 追踪
3. 使用 IDE 断点
4. 添加日志：
```python
from src.utils import app_logger
app_logger.debug("调试信息")
```

### Q: 如何添加新的 API 端点？

**A:**

```python
# src/api/routes.py
@router.post("/new-endpoint")
async def new_endpoint(request: NewRequest):
    """端点描述"""
    try:
        # 处理逻辑
        return {"result": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## 其他问题

### Q: 项目的许可证是什么？

**A:** MIT License。你可以自由使用、修改和分发。

### Q: 如何报告 Bug？

**A:** 在 GitHub 上提交 [Issue](https://github.com/wssaidong/cus-ai-agent/issues/new)，包含：
- 问题描述
- 复现步骤
- 错误日志
- 环境信息

### Q: 有社区支持吗？

**A:** 
- GitHub Issues: 技术问题
- GitHub Discussions: 讨论和交流
- 文档: 详细的使用指南

### Q: 项目的路线图是什么？

**A:** 查看 [CHANGELOG.md](../CHANGELOG.md) 和 GitHub Issues。

### Q: 如何获取更多帮助？

**A:**
1. 查看 [文档](../README.md)
2. 搜索 [Issues](https://github.com/wssaidong/cus-ai-agent/issues)
3. 阅读 [故障排查指南](troubleshooting.md)
4. 提交新的 Issue

---

没有找到你的问题？请提交 [Issue](https://github.com/wssaidong/cus-ai-agent/issues/new) 或查看 [故障排查指南](troubleshooting.md)。

