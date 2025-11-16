#!/bin/bash

# ==========================================
# cus-ai-agent 服务启动脚本
# ==========================================
#
# 用途: 启动 AI Agent API 服务
# 使用: ./scripts/start.sh [选项]
#
# 选项:
#   --dev         开发模式（启用自动重载）
#   --port PORT   指定端口（默认: 8000）
#   --host HOST   指定主机（默认: 0.0.0.0）
#   --workers N   工作进程数（默认: 1）
#   --check       仅检查环境，不启动服务
#   --help        显示帮助信息
#
# 示例:
#   ./scripts/start.sh                    # 生产模式启动
#   ./scripts/start.sh --dev              # 开发模式启动
#   ./scripts/start.sh --port 8080        # 指定端口
#   ./scripts/start.sh --workers 4        # 4个工作进程
# ==========================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 默认配置
DEV_MODE=false
PORT=8000
HOST="0.0.0.0"
WORKERS=1
CHECK_ONLY=false

# 打印函数
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

print_header() {
    echo -e "${CYAN}$1${NC}"
}

# 使用 pip 安装依赖，增加镜像和超时支持
install_requirements() {
    # 优先使用环境变量 PIP_INDEX_URL，其次使用清华镜像
    local index_url="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
    print_info "使用 pip 安装依赖 (index-url: $index_url)"

    pip install -r requirements.txt \
        -i "$index_url" \
        --timeout "${PIP_TIMEOUT:-600}" \
        --retries "${PIP_RETRIES:-5}"
}

# 显示帮助信息
show_help() {
    cat << EOF
${CYAN}cus-ai-agent 服务启动脚本${NC}

用法: $0 [选项]

选项:
  --dev              开发模式（启用自动重载）
  --port PORT        指定端口（默认: 8000）
  --host HOST        指定主机（默认: 0.0.0.0）
  --workers N        工作进程数（默认: 1）
  --check            仅检查环境，不启动服务
  --help             显示此帮助信息

示例:
  $0                           # 生产模式启动
  $0 --dev                     # 开发模式启动
  $0 --port 8080               # 指定端口
  $0 --workers 4               # 4个工作进程
  $0 --dev --port 8080         # 开发模式 + 自定义端口

环境变量:
  UVICORN_RELOAD=true          启用自动重载
  API_PORT=8000                API 端口
  API_HOST=0.0.0.0             API 主机

EOF
    exit 0
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            DEV_MODE=true
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --check)
            CHECK_ONLY=true
            shift
            ;;
        --help)
            show_help
            ;;
        *)
            print_error "未知选项: $1"
            echo "使用 --help 查看帮助信息"
            exit 1
            ;;
    esac
done

# 打印标题
clear
echo ""
print_header "=========================================="
print_header "  🚀 cus-ai-agent 服务启动"
print_header "=========================================="
echo ""

# 检查是否在项目根目录
if [ ! -f "run.py" ]; then
    print_error "未找到 run.py 文件"
    print_info "请在项目根目录运行此脚本"
    exit 1
fi

print_success "项目根目录检查通过"

# 检查 Python 环境
print_info "检查 Python 环境..."
if ! command -v python &> /dev/null; then
    print_error "未找到 Python"
    print_info "请先安装 Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
print_success "Python 版本: $PYTHON_VERSION"

# 检查虚拟环境
if [ -z "$VIRTUAL_ENV" ]; then
    print_warning "未检测到虚拟环境"

    if [ -d "venv" ]; then
        print_info "发现 venv 目录，尝试激活..."
        source venv/bin/activate
        if [ $? -eq 0 ]; then
            print_success "虚拟环境已激活: $VIRTUAL_ENV"
        else
            print_error "虚拟环境激活失败"
            exit 1
        fi
    else
        print_warning "建议创建虚拟环境: python -m venv venv"
        read -p "是否继续使用系统 Python? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    print_success "虚拟环境已激活: $VIRTUAL_ENV"
fi

# 检查 .env 文件
print_info "检查环境配置..."
if [ ! -f ".env" ]; then
    print_warning "未找到 .env 文件"
    if [ -f ".env.example" ]; then
        print_info "发现 .env.example"
        read -p "是否复制为 .env? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cp .env.example .env
            print_success "已创建 .env 文件"
            print_warning "请编辑 .env 文件配置必要的环境变量"
            print_info "特别是: OPENAI_API_KEY, OPENAI_API_BASE"
            read -p "配置完成后按回车继续..." -r
        else
            print_error "需要 .env 文件才能启动服务"
            exit 1
        fi
    else
        print_error "未找到 .env 或 .env.example 文件"
        exit 1
    fi
else
    print_success "找到 .env 配置文件"
fi

# 检查依赖
print_info "检查依赖包..."
if [ -f "requirements.txt" ]; then
    # 检查关键依赖
    MISSING_DEPS=()

    if ! python -c "import fastapi" 2>/dev/null; then
        MISSING_DEPS+=("fastapi")
    fi

    if ! python -c "import langgraph" 2>/dev/null; then
        MISSING_DEPS+=("langgraph")
    fi

    if ! python -c "import langchain" 2>/dev/null; then
        MISSING_DEPS+=("langchain")
    fi

    if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
        print_warning "缺少依赖: ${MISSING_DEPS[*]}"
        read -p "是否安装依赖? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "安装依赖..."
            install_requirements
            if [ $? -eq 0 ]; then
                print_success "依赖安装成功"
            else
                print_error "依赖安装失败"
                exit 1
            fi
        else
            print_error "缺少必要依赖，无法启动服务"
            exit 1
        fi
    else
        print_success "依赖检查通过"
    fi
fi

# 检查 LangGraph 版本
print_info "检查 LangGraph 版本..."
LANGGRAPH_VERSION=$(python -c "import langgraph; print(langgraph.__version__)" 2>/dev/null || echo "unknown")
if [[ "$LANGGRAPH_VERSION" == "unknown" ]]; then
    print_error "无法获取 LangGraph 版本"
else
    print_success "LangGraph 版本: $LANGGRAPH_VERSION"

    # 检查是否为 1.0+ 版本
    MAJOR_VERSION=$(echo $LANGGRAPH_VERSION | cut -d. -f1)
    if [ "$MAJOR_VERSION" -lt 1 ]; then
        print_warning "LangGraph 版本低于 1.0，建议升级"
        print_info "运行: pip install langgraph>=1.0.0"
    fi
fi

# 检查端口占用
print_info "检查端口 $PORT..."
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    print_warning "端口 $PORT 已被占用"

    # 显示占用进程
    PID=$(lsof -Pi :$PORT -sTCP:LISTEN -t)
    PROCESS=$(ps -p $PID -o comm= 2>/dev/null || echo "unknown")
    print_info "占用进程: $PROCESS (PID: $PID)"

    read -p "是否终止该进程? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill $PID
        sleep 1
        print_success "进程已终止"
    else
        print_error "端口被占用，无法启动服务"
        exit 1
    fi
else
    print_success "端口 $PORT 可用"
fi

# 如果只是检查环境
if [ "$CHECK_ONLY" = true ]; then
    echo ""
    print_success "环境检查完成，所有检查通过！"
    exit 0
fi

# 显示启动配置
echo ""
print_header "=========================================="
print_header "  📋 启动配置"
print_header "=========================================="
echo ""
echo "  模式:     $([ "$DEV_MODE" = true ] && echo "开发模式 (自动重载)" || echo "生产模式")"
echo "  主机:     $HOST"
echo "  端口:     $PORT"
echo "  工作进程: $WORKERS"
echo "  Python:   $PYTHON_VERSION"
echo "  LangGraph: $LANGGRAPH_VERSION"
echo ""

# 启动服务
echo ""
print_header "=========================================="
print_header "  🎯 启动服务"
print_header "=========================================="
echo ""

if [ "$DEV_MODE" = true ]; then
    # 开发模式
    print_info "开发模式启动（自动重载已启用）"
    export UVICORN_RELOAD=true
    python run.py
else
    # 生产模式
    print_info "生产模式启动"

    if [ "$WORKERS" -gt 1 ]; then
        print_info "使用 $WORKERS 个工作进程"
        # 使用 gunicorn
        if command -v gunicorn &> /dev/null; then
            gunicorn src.api.main:app \
                --workers $WORKERS \
                --worker-class uvicorn.workers.UvicornWorker \
                --bind $HOST:$PORT \
                --access-logfile - \
                --error-logfile -
        else
            print_warning "未找到 gunicorn，使用单进程模式"
            python run.py
        fi
    else
        python run.py
    fi
fi

# 服务停止
echo ""
print_info "服务已停止"

