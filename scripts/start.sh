#!/bin/bash

# 智能体服务启动脚本

set -e

echo "================================"
echo "启动智能体API服务"
echo "================================"

# 检查Python版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python版本: $python_version"

# 检查是否存在虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 升级pip
echo "升级pip..."
pip install --upgrade pip

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "警告: .env文件不存在，使用.env.example创建..."
    cp .env.example .env
    echo "请编辑.env文件，配置必要的环境变量（如OPENAI_API_KEY）"
    exit 1
fi

# 创建日志目录
mkdir -p logs

# 启动服务
echo "启动服务..."
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

echo "================================"
echo "服务已启动"
echo "API文档: http://localhost:8000/docs"
echo "================================"

