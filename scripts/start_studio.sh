#!/bin/bash

# ==========================================
# LangGraph Studio 启动脚本
# ==========================================
# 
# 用途: 启动 LangGraph Studio 开发服务器
# 使用: ./scripts/start_studio.sh
#
# 功能:
# - 检查并安装 langgraph-cli
# - 启动开发服务器
# - 自动打开 Studio UI
# ==========================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 打印标题
echo ""
echo "=========================================="
echo "  🚀 LangGraph Studio 启动脚本"
echo "=========================================="
echo ""

# 检查是否在项目根目录
if [ ! -f "langgraph.json" ]; then
    print_error "未找到 langgraph.json 文件"
    print_info "请在项目根目录运行此脚本"
    exit 1
fi

print_success "找到 langgraph.json 配置文件"

# 检查 Python 环境
if ! command -v python &> /dev/null; then
    print_error "未找到 Python,请先安装 Python 3.8+"
    exit 1
fi

print_success "Python 环境检查通过"

# 检查虚拟环境
if [ -z "$VIRTUAL_ENV" ]; then
    print_warning "未检测到虚拟环境"
    print_info "建议激活虚拟环境: source venv/bin/activate"
    read -p "是否继续? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    print_success "虚拟环境已激活: $VIRTUAL_ENV"
fi

# 检查是否安装了 langgraph-cli
print_info "检查 langgraph CLI..."
if ! command -v langgraph &> /dev/null; then
    print_warning "未找到 langgraph CLI"
    print_info "正在安装 langgraph-cli..."
    
    pip install langgraph-cli
    
    if [ $? -eq 0 ]; then
        print_success "langgraph-cli 安装成功"
    else
        print_error "langgraph-cli 安装失败"
        exit 1
    fi
else
    print_success "langgraph CLI 已安装"
    
    # 显示版本信息
    LANGGRAPH_VERSION=$(langgraph --version 2>&1 || echo "unknown")
    print_info "版本: $LANGGRAPH_VERSION"
fi

# 检查 .env 文件
if [ ! -f ".env" ]; then
    print_warning "未找到 .env 文件"
    if [ -f ".env.example" ]; then
        print_info "发现 .env.example,是否复制为 .env? (y/n)"
        read -p "" -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cp .env.example .env
            print_success "已创建 .env 文件,请配置必要的环境变量"
            print_warning "特别是 OPENAI_API_KEY 等关键配置"
        fi
    fi
else
    print_success "找到 .env 配置文件"
fi

# 检查端口占用
PORT=8123
print_info "检查端口 $PORT 是否可用..."
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    print_warning "端口 $PORT 已被占用"
    print_info "将尝试使用其他端口..."
    PORT=8124
fi

print_success "将使用端口: $PORT"

# 启动服务器
echo ""
echo "=========================================="
echo "  📊 启动 LangGraph Studio 服务器"
echo "=========================================="
echo ""

print_info "启动命令: langgraph dev --port $PORT"
print_info "Studio UI 将在浏览器中自动打开"
print_info "访问地址: http://localhost:$PORT"
echo ""
print_warning "按 Ctrl+C 停止服务器"
echo ""

# 启动开发服务器
if [ "$PORT" = "8123" ]; then
    langgraph dev
else
    langgraph dev --port $PORT
fi

# 如果服务器停止
echo ""
print_info "服务器已停止"

