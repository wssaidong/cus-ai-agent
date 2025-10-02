# 故障排查指南

本文档帮助你解决常见问题。

## 📋 目录

- [安装问题](#安装问题)
- [启动问题](#启动问题)
- [API 调用问题](#api-调用问题)
- [工具调用问题](#工具调用问题)
- [RAG 知识库问题](#rag-知识库问题)
- [性能问题](#性能问题)
- [日志和调试](#日志和调试)

## 安装问题

### 问题：pip 安装依赖失败

**症状**
```bash
ERROR: Could not find a version that satisfies the requirement...
```

**解决方案**

1. 升级 pip
```bash
pip install --upgrade pip
```

2. 使用国内镜像
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

3. 检查 Python 版本
```bash
python --version  # 需要 3.10+
```

### 问题：虚拟环境创建失败

**症状**
```bash
Error: Command '...' returned non-zero exit status 1
```

**解决方案**

1. 安装 venv 模块
```bash
# Ubuntu/Debian
sudo apt-get install python3-venv

# macOS
brew install python@3.10
```

2. 使用 virtualenv
```bash
pip install virtualenv
virtualenv venv
```

### 问题：Pydantic v2 兼容性错误

**症状**
```
ValidationError: 1 validation error for XXX
```

**解决方案**

1. 确保使用 LangChain 0.3+
```bash
pip install --upgrade langchain langchain-core langchain-community
```

2. 运行升级脚本
```bash
python scripts/upgrade_langchain.py
```

## 启动问题

### 问题：端口被占用

**症状**
```
ERROR: [Errno 48] Address already in use
```

**解决方案**

1. 查找占用端口的进程
```bash
# macOS/Linux
lsof -i :8000

# Windows
netstat -ano | findstr :8000
```

2. 杀死进程
```bash
# macOS/Linux
kill -9 <PID>

# Windows
taskkill /PID <PID> /F
```

3. 或修改端口
```bash
# 在 .env 中
API_PORT=8001
```

### 问题：环境变量未加载

**症状**
```
KeyError: 'OPENAI_API_KEY'
```

**解决方案**

1. 确认 .env 文件存在
```bash
ls -la .env
```

2. 检查环境变量格式
```bash
# 正确格式
OPENAI_API_KEY=sk-xxx

# 错误格式（不要有空格）
OPENAI_API_KEY = sk-xxx
```

3. 手动加载环境变量
```bash
export $(cat .env | xargs)
python run.py
```

### 问题：模块导入错误

**症状**
```
ModuleNotFoundError: No module named 'src'
```

**解决方案**

1. 确保在项目根目录
```bash
pwd  # 应该显示 .../cus-ai-agent
```

2. 设置 PYTHONPATH
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

3. 使用模块方式运行
```bash
python -m uvicorn src.api.main:app
```

## API 调用问题

### 问题：API 返回 500 错误

**症状**
```json
{
  "error": "Internal Server Error",
  "detail": "..."
}
```

**解决方案**

1. 查看日志
```bash
tail -f logs/app_$(date +%Y-%m-%d).log
```

2. 检查 API Key
```bash
# 测试 OpenAI API
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

3. 启用调试模式
```bash
# 在 .env 中
LOG_LEVEL=DEBUG
```

### 问题：请求超时

**症状**
```
ReadTimeout: HTTPSConnectionPool...
```

**解决方案**

1. 增加超时时间
```bash
# 在 .env 中
TIMEOUT_SECONDS=60
```

2. 检查网络连接
```bash
ping api.openai.com
```

3. 使用代理
```bash
# 在 .env 中
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080
```

### 问题：响应格式错误

**症状**
```
JSONDecodeError: Expecting value...
```

**解决方案**

1. 检查请求格式
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'
```

2. 查看 API 文档
```
http://localhost:8000/docs
```

## 工具调用问题

### 问题：工具未被调用

**症状**

智能体没有使用工具，直接返回答案。

**解决方案**

1. 检查工具是否启用
```bash
# 在 .env 中
ENABLE_API_TOOL=true
ENABLE_DATABASE_TOOL=true
```

2. 查看可用工具
```python
from src.tools import get_available_tools
tools = get_available_tools()
print([tool.name for tool in tools])
```

3. 优化提示词
```python
# 明确要求使用工具
message = "请使用计算器工具计算 123 + 456"
```

### 问题：数据库工具连接失败

**症状**
```
OperationalError: could not connect to server
```

**解决方案**

1. 检查数据库 URL
```bash
# 在 .env 中
DATABASE_URL=postgresql://user:pass@localhost:5432/db
```

2. 测试连接
```bash
psql $DATABASE_URL
```

3. 检查数据库服务
```bash
# PostgreSQL
sudo systemctl status postgresql

# MySQL
sudo systemctl status mysql
```

## RAG 知识库问题

### 问题：Milvus 连接失败

**症状**
```
MilvusException: <MilvusException: (code=1, message=Fail connecting to server...)>
```

**解决方案**

1. 启动 Milvus
```bash
./scripts/start_milvus.sh
```

2. 检查 Milvus 状态
```bash
docker ps | grep milvus
```

3. 检查配置
```bash
# 在 .env 中
RAG_MILVUS_HOST=localhost
RAG_MILVUS_PORT=19530
```

4. 测试连接
```python
from pymilvus import connections
connections.connect(host="localhost", port="19530")
```

### 问题：文档上传失败

**症状**
```
ValueError: 不支持的文件格式
```

**解决方案**

1. 检查文件格式
```bash
# 支持的格式
.txt, .md, .pdf, .docx
```

2. 查看支持的格式
```bash
curl http://localhost:8000/api/v1/knowledge/supported-formats
```

3. 检查文件大小
```bash
# 默认限制 10MB
ls -lh document.pdf
```

### 问题：检索结果不准确

**症状**

搜索返回不相关的结果。

**解决方案**

1. 调整 top_k 参数
```python
{
  "query": "搜索内容",
  "top_k": 10  # 增加返回数量
}
```

2. 优化文档分割
```python
# 在 src/tools/rag_tool.py 中
chunk_size = 500  # 减小分块大小
chunk_overlap = 50  # 增加重叠
```

3. 使用更好的 Embedding 模型
```bash
# 在 .env 中
RAG_EMBEDDING_MODEL=text-embedding-3-large
```

## 性能问题

### 问题：响应速度慢

**症状**

API 响应时间超过 10 秒。

**解决方案**

1. 启用缓存
```python
# 添加 Redis 缓存
REDIS_URL=redis://localhost:6379
```

2. 减少 max_tokens
```bash
# 在 .env 中
MAX_TOKENS=1000
```

3. 使用更快的模型
```bash
# 在 .env 中
MODEL_NAME=gpt-3.5-turbo
```

4. 启用流式输出
```python
# 使用 /api/v1/chat/stream
```

### 问题：内存占用高

**症状**

服务占用大量内存。

**解决方案**

1. 限制并发请求
```python
# 使用 Gunicorn
gunicorn -w 2 --worker-class uvicorn.workers.UvicornWorker
```

2. 清理向量库
```bash
curl -X DELETE "http://localhost:8000/api/v1/knowledge/clear"
```

3. 重启服务
```bash
./scripts/restart.sh
```

## 日志和调试

### 启用详细日志

```bash
# 在 .env 中
LOG_LEVEL=DEBUG
LOG_FORMAT=text  # 或 json
```

### 查看日志

```bash
# 实时查看
tail -f logs/app_$(date +%Y-%m-%d).log

# 搜索错误
grep ERROR logs/app_*.log

# 查看最近的日志
tail -n 100 logs/app_$(date +%Y-%m-%d).log
```

### 使用 LangSmith 调试

```bash
# 在 .env 中启用
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_key

# 访问 https://smith.langchain.com/
```

### Python 调试

```python
# 添加断点
import pdb; pdb.set_trace()

# 或使用 IDE 断点调试
```

## 获取帮助

如果以上方法都无法解决问题：

1. 查看 [文档](../README.md)
2. 搜索 [Issues](https://github.com/wssaidong/cus-ai-agent/issues)
3. 提交新的 [Issue](https://github.com/wssaidong/cus-ai-agent/issues/new)
4. 查看 [FAQ](faq.md)

提交 Issue 时请包含：

- 问题描述
- 复现步骤
- 错误日志
- 环境信息（Python 版本、操作系统等）
- 配置信息（隐藏敏感信息）

---

希望这个指南能帮助你解决问题！🔧

