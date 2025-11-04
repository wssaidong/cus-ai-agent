#!/bin/bash

# ==========================================
# cus-ai-agent 服务停止脚本
# ==========================================
# 
# 用途: 停止 AI Agent API 服务
# 使用: ./scripts/stop.sh [选项]
#
# 选项:
#   --port PORT   指定端口（默认: 8000）
#   --force       强制终止
#   --all         停止所有相关进程
#   --help        显示帮助信息
# ==========================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 默认配置
PORT=8000
FORCE=false
STOP_ALL=false

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

# 显示帮助
show_help() {
    cat << EOF
${CYAN}服务停止脚本${NC}

用法: $0 [选项]

选项:
  --port PORT    指定端口（默认: 8000）
  --force        强制终止（使用 kill -9）
  --all          停止所有相关进程
  --help         显示此帮助信息

示例:
  $0                    # 停止默认端口服务
  $0 --port 8080        # 停止指定端口服务
  $0 --force            # 强制终止
  $0 --all              # 停止所有相关进程

EOF
    exit 0
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --all)
            STOP_ALL=true
            shift
            ;;
        --help)
            show_help
            ;;
        *)
            print_error "未知选项: $1"
            exit 1
            ;;
    esac
done

# 打印标题
echo ""
print_header "=========================================="
print_header "  🛑 停止服务"
print_header "=========================================="
echo ""

# 停止指定端口的进程
stop_by_port() {
    local port=$1
    
    print_info "检查端口 $port..."
    
    if ! lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        print_warning "端口 $port 没有运行的服务"
        return 1
    fi
    
    # 获取进程信息
    PIDS=$(lsof -Pi :$port -sTCP:LISTEN -t)
    
    for PID in $PIDS; do
        PROCESS=$(ps -p $PID -o comm= 2>/dev/null || echo "unknown")
        print_info "发现进程: $PROCESS (PID: $PID)"
        
        if [ "$FORCE" = true ]; then
            print_warning "强制终止进程 $PID..."
            kill -9 $PID 2>/dev/null || true
        else
            print_info "正常终止进程 $PID..."
            kill $PID 2>/dev/null || true
        fi
        
        # 等待进程结束
        sleep 1
        
        # 检查进程是否还在运行
        if ps -p $PID > /dev/null 2>&1; then
            print_warning "进程 $PID 仍在运行，尝试强制终止..."
            kill -9 $PID 2>/dev/null || true
            sleep 1
        fi
        
        # 再次检查
        if ps -p $PID > /dev/null 2>&1; then
            print_error "无法终止进程 $PID"
        else
            print_success "进程 $PID 已停止"
        fi
    done
    
    return 0
}

# 停止所有相关进程
stop_all_processes() {
    print_info "查找所有相关进程..."
    
    # 查找 Python 进程中包含 run.py 或 uvicorn 的
    PIDS=$(ps aux | grep -E "(run.py|uvicorn.*cus-ai-agent)" | grep -v grep | awk '{print $2}')
    
    if [ -z "$PIDS" ]; then
        print_warning "未找到相关进程"
        return 1
    fi
    
    for PID in $PIDS; do
        PROCESS=$(ps -p $PID -o command= 2>/dev/null || echo "unknown")
        print_info "发现进程: $PROCESS"
        print_info "PID: $PID"
        
        if [ "$FORCE" = true ]; then
            print_warning "强制终止进程 $PID..."
            kill -9 $PID 2>/dev/null || true
        else
            print_info "正常终止进程 $PID..."
            kill $PID 2>/dev/null || true
        fi
        
        sleep 1
        
        if ps -p $PID > /dev/null 2>&1; then
            print_warning "进程 $PID 仍在运行，尝试强制终止..."
            kill -9 $PID 2>/dev/null || true
        fi
        
        if ps -p $PID > /dev/null 2>&1; then
            print_error "无法终止进程 $PID"
        else
            print_success "进程 $PID 已停止"
        fi
    done
    
    return 0
}

# 执行停止操作
if [ "$STOP_ALL" = true ]; then
    stop_all_processes
else
    stop_by_port $PORT
fi

# 验证
echo ""
print_info "验证服务状态..."

if [ "$STOP_ALL" = true ]; then
    REMAINING=$(ps aux | grep -E "(run.py|uvicorn.*cus-ai-agent)" | grep -v grep | wc -l)
    if [ $REMAINING -eq 0 ]; then
        print_success "所有服务已停止"
    else
        print_warning "仍有 $REMAINING 个相关进程在运行"
    fi
else
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        print_warning "端口 $PORT 仍被占用"
    else
        print_success "端口 $PORT 已释放"
    fi
fi

echo ""
print_success "操作完成"

