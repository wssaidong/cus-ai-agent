# 快速开始指南

本指南将帮助你在5分钟内启动并运行智能体API服务。

## 前置要求

- Python 3.10 或更高版本
- OpenAI API密钥（或其他兼容的LLM API）
- 终端/命令行工具

## 步骤1：获取代码

```bash
git clone <repository-url>
cd cus-ai-agent
```

## 步骤2：配置环境

### 创建虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

### 安装依赖

```bash
# 升级pip（重要！避免安装错误）
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

> 💡 **提示**: 如果遇到安装问题，请查看[故障排查指南](troubleshooting.md)

## 步骤3：配置API密钥

### 复制环境变量文件

```bash
cp .env.example .env
```

### 编辑.env文件

打开`.env`文件，至少配置以下内容：

```env
OPENAI_API_KEY=sk-your-api-key-here
```

> 💡 提示：你可以从 https://platform.openai.com/api-keys 获取API密钥

## 步骤4：启动服务

### 方式一：使用Python启动脚本（推荐）

```bash
python run.py
```

### 方式二：使用Shell脚本

```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

### 方式三：直接运行

```bash
# 如果使用虚拟环境，先激活
source venv/bin/activate

# 启动服务
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

## 步骤5：验证服务

### 访问API文档

在浏览器中打开：http://localhost:8000/docs

你将看到交互式的API文档界面。

### 测试健康检查

```bash
curl http://localhost:8000/api/v1/health
```

预期响应：
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T12:00:00"
}
```

## 步骤6：发送第一个请求

### 使用cURL

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，请介绍一下你自己",
    "session_id": "test-001"
  }'
```

### 使用Python

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/chat",
    json={
        "message": "你好，请介绍一下你自己",
        "session_id": "test-001"
    }
)

print(response.json())
```

### 在API文档中测试

1. 访问 http://localhost:8000/docs
2. 找到 `POST /api/v1/chat` 接口
3. 点击 "Try it out"
4. 输入请求参数
5. 点击 "Execute"

## 常用功能示例

### 1. 使用计算器

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "帮我计算 123 + 456"
  }'
```

### 2. 文本处理

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "请把 hello world 转换为大写"
  }'
```

### 3. 流式输出

```bash
curl -X POST "http://localhost:8000/api/v1/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "请详细介绍一下人工智能"
  }'
```

## 运行测试

### 运行API测试脚本

```bash
chmod +x scripts/test_api.sh
./scripts/test_api.sh
```

### 运行单元测试

```bash
pytest tests/
```

## 下一步

恭喜！你已经成功启动了智能体API服务。接下来你可以：

1. 📖 阅读[完整文档](../README.md)了解更多功能
2. 🛠️ 查看[使用示例](usage_examples.md)学习高级用法
3. 🏗️ 阅读[架构设计](architecture.md)了解系统设计
4. 🚀 查看[部署指南](deployment.md)了解生产环境部署
5. 🔧 自定义工具和智能体流程

## 常见问题

### Q: 启动失败，提示端口被占用

**A:** 修改`.env`文件中的`API_PORT`为其他端口，例如：

```env
API_PORT=8001
```

### Q: API调用失败，提示认证错误

**A:** 检查`.env`文件中的`OPENAI_API_KEY`是否正确配置。

### Q: 如何更换其他大模型？

**A:** 修改`.env`文件中的模型配置：

```env
MODEL_NAME=gpt-3.5-turbo
# 或
MODEL_NAME=gpt-4
```

### Q: 如何查看日志？

**A:** 日志文件位于`logs/`目录下：

```bash
tail -f logs/app_*.log
```

### Q: 如何停止服务？

**A:** 在终端中按 `Ctrl+C` 停止服务。

## 获取帮助

如果遇到问题：

1. 查看[完整文档](../README.md)
2. 查看日志文件：`logs/app_*.log`
3. 提交Issue到项目仓库
4. 联系维护者

## 总结

你已经学会了：

- ✅ 安装和配置环境
- ✅ 启动智能体API服务
- ✅ 发送API请求
- ✅ 使用基本工具功能
- ✅ 运行测试

现在你可以开始构建自己的智能体应用了！🎉

