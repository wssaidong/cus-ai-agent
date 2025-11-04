#!/bin/bash

# 依赖安装脚本

echo "================================"
echo "安装项目依赖"
echo "================================"

# 检查Python版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python版本: $python_version"

# 检查是否存在虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
    echo "✅ 虚拟环境创建成功"
else
    echo "✅ 虚拟环境已存在"
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 升级pip
echo "升级pip..."
pip install --upgrade pip -q

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

echo ""
echo "================================"
echo "✅ 依赖安装完成"
echo "================================"
echo ""
echo "下一步:"
echo "1. 配置环境变量: cp .env.example .env"
echo "2. 编辑.env文件，设置OPENAI_API_KEY"
echo "3. 启动服务: python run.py"
echo ""

