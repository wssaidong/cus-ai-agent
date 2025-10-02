# 快速开始指南

本指南将帮助你在 **5 分钟**内启动并运行智能体 API 服务。

## 📋 前置要求

- **Python**: 3.10+ (推荐 3.11)
- **OpenAI API Key**: 或其他兼容的 LLM API
- **Docker**: (可选) 用于 Milvus 向量数据库

检查 Python 版本:
```bash
python --version  # 应该 >= 3.10
```

---

## 🚀 快速启动 (3 步)

### 步骤 1: 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd cus-ai-agent

# 使用安装脚本 (推荐)
chmod +x scripts/install.sh
./scripts/install.sh
```

或手动安装:
```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 升级 pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

> 💡 **提示**: 如果遇到 Pydantic v2 兼容性问题,运行 `python scripts/upgrade_langchain.py`

---

### 步骤 2: 配置环境变量

```bash
# 复制配置文件
cp .env.example .env

# 编辑配置 (必须设置 OPENAI_API_KEY)
nano .env  # 或使用其他编辑器
```

**最小配置** (.env 文件):
```env
# 必需
OPENAI_API_KEY=sk-your-api-key-here

# 可选 (使用默认值)
MODEL_NAME=gpt-3.5-turbo
TEMPERATURE=0.7
```

> 💡 **获取 API Key**: https://platform.openai.com/api-keys

---

### 步骤 3: 启动服务

```bash
python run.py
```

服务启动后,你会看到:
```
🚀 启动智能体API服务
Python版本: 3.11.x
✅ .env文件已存在
✅ 日志目录已创建

启动服务...
API文档: http://localhost:8000/docs
健康检查: http://localhost:8000/api/v1/health
```

---

## ✅ 验证安装

### 1. 测试健康检查

```bash
curl http://localhost:8000/api/v1/health
```

预期响应:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### 2. 访问 API 文档

浏览器打开: **http://localhost:8000/docs**

你将看到交互式的 Swagger UI 文档。

### 3. 发送第一个请求

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "session_id": "test-001"}'
```

---

## 🎯 下一步

恭喜!你已经成功启动了智能体服务。接下来可以:

1. 📖 查看 [使用示例](usage_examples.md) - 学习更多 API 用法
2. 🏗️ 阅读 [架构设计](architecture.md) - 了解系统设计
3. 📊 启用 [LangSmith 监控](langsmith_integration.md) - 追踪和调试
4. 🔧 集成 [RAG 知识库](rag_milvus_integration.md) - 添加知识检索
5. 🚀 查看 [部署指南](deployment.md) - 生产环境部署

---

## 🔧 可选配置

### 启用 LangSmith 追踪

在 `.env` 中添加:
```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=cus-ai-agent
```

### 启用 RAG 知识库

```bash
# 1. 启动 Milvus
./scripts/start_milvus.sh

# 2. 配置 .env
ENABLE_RAG_TOOL=true
RAG_MILVUS_HOST=localhost
RAG_MILVUS_PORT=19530
```

### 更换模型

在 `.env` 中修改:
```env
MODEL_NAME=gpt-4-turbo-preview  # 或其他模型
```

---

## ❓ 常见问题

### Q: 启动失败,提示端口被占用

**A**: 修改 `.env` 中的端口:
```env
API_PORT=8001
```

### Q: API 调用失败,提示认证错误

**A**: 检查 `OPENAI_API_KEY` 是否正确配置。

### Q: 遇到 Pydantic v2 兼容性问题

**A**: 运行升级脚本:
```bash
python scripts/upgrade_langchain.py
python scripts/test_import.py  # 验证
```

### Q: 如何查看日志?

**A**: 日志文件在 `logs/` 目录:
```bash
tail -f logs/app_*.log
```

### Q: 如何停止服务?

**A**: 在终端按 `Ctrl+C`

---

## 📚 完整安装指南

如果需要更详细的安装说明,包括:
- 系统要求
- Python 环境配置
- 虚拟环境管理
- 依赖问题排查
- Docker 部署

请查看完整的安装文档 (以下内容整合自 INSTALL.md):

### 系统要求

| 项目 | 要求 |
|------|------|
| **Python** | 3.10+ (推荐 3.11) |
| **操作系统** | macOS, Linux, Windows |
| **内存** | 最低 4GB, 推荐 8GB |
| **磁盘** | 最低 2GB 可用空间 |
| **Docker** | (可选) 用于 Milvus |

### Python 环境配置

#### macOS

```bash
# 使用 Homebrew 安装
brew install python@3.11

# 验证
python3 --version
```

#### Linux (Ubuntu/Debian)

```bash
# 安装 Python 3.11
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# 验证
python3.11 --version
```

#### Windows

1. 下载 Python 3.11: https://www.python.org/downloads/
2. 安装时勾选 "Add Python to PATH"
3. 验证: `python --version`

### 虚拟环境管理

#### 创建虚拟环境

```bash
# 使用 venv (推荐)
python3 -m venv venv

# 或使用 conda
conda create -n cus-ai-agent python=3.11
```

#### 激活虚拟环境

```bash
# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate

# Conda
conda activate cus-ai-agent
```

#### 停用虚拟环境

```bash
deactivate  # venv
conda deactivate  # conda
```

### 依赖安装详解

#### 核心依赖

```bash
# 升级 pip (重要!)
pip install --upgrade pip setuptools wheel

# 安装核心依赖
pip install -r requirements.txt
```

#### 验证安装

```bash
# 运行测试脚本
python scripts/test_import.py
```

预期输出:
```
✓ 核心包导入成功
✓ LangChain OpenAI 导入成功
✓ Pydantic v2 兼容
✓ ChatOpenAI 实例创建成功
✓ LangGraph 导入成功
✓ LangSmith 导入成功
✓ 所有测试通过!
```

### 环境变量配置详解

#### 必需配置

```env
# OpenAI API
OPENAI_API_KEY=sk-xxx  # 必需
OPENAI_API_BASE=https://api.openai.com/v1
```

#### 模型配置

```env
MODEL_NAME=gpt-3.5-turbo  # 默认模型
TEMPERATURE=0.7           # 温度参数 (0-2)
MAX_TOKENS=2000          # 最大 token 数
```

#### API 配置

```env
API_HOST=0.0.0.0
API_PORT=8000
API_TITLE=智能体API服务
```

#### 日志配置

```env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json # json 或 text
```

#### 工具配置

```env
ENABLE_DATABASE_TOOL=false
ENABLE_API_TOOL=true
ENABLE_RAG_TOOL=false
```

### Docker 部署

#### 使用 Docker Compose

```bash
# 启动所有服务 (包括 Milvus)
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

#### 仅启动智能体服务

```bash
# 构建镜像
docker build -t cus-ai-agent .

# 运行容器
docker run -d \
  --name cus-ai-agent \
  -p 8000:8000 \
  --env-file .env \
  cus-ai-agent
```

---

## 🆘 获取帮助

如果遇到问题:

1. 查看 [故障排查指南](troubleshooting.md)
2. 查看日志: `tail -f logs/app_*.log`
3. 运行测试: `python scripts/test_import.py`
4. 提交 Issue 到 GitHub

---

**文档版本**: v2.0
**最后更新**: 2025-10-02