#!/bin/bash

# ==========================================
# Docker 镜像构建脚本
# ==========================================
# 功能:
# 1. 支持普通构建和强制重新构建
# 2. 自动添加版本标签
# 3. 构建后验证
# ==========================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
IMAGE_NAME="cus-ai-agent"
VERSION=$(date +%Y%m%d-%H%M%S)
NO_CACHE=false
PUSH=false

# 显示帮助信息
show_help() {
    echo -e "${BLUE}Docker 镜像构建脚本${NC}"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -n, --no-cache    强制重新构建,不使用缓存"
    echo "  -v, --version     指定版本标签 (默认: 时间戳)"
    echo "  -p, --push        构建后推送到镜像仓库"
    echo "  -h, --help        显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                      # 普通构建"
    echo "  $0 --no-cache           # 强制重新构建"
    echo "  $0 -v v1.0.0            # 指定版本号"
    echo "  $0 -v v1.0.0 --push     # 构建并推送"
    echo ""
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--no-cache)
            NO_CACHE=true
            shift
            ;;
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -p|--push)
            PUSH=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}未知选项: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# 显示构建信息
echo -e "${BLUE}======================================"
echo "Docker 镜像构建"
echo "======================================${NC}"
echo -e "镜像名称: ${GREEN}${IMAGE_NAME}${NC}"
echo -e "版本标签: ${GREEN}${VERSION}${NC}"
echo -e "强制重建: ${GREEN}${NO_CACHE}${NC}"
echo -e "推送镜像: ${GREEN}${PUSH}${NC}"
echo ""

# 检查 Dockerfile 是否存在
if [ ! -f "Dockerfile" ]; then
    echo -e "${RED}✗ 错误: 找不到 Dockerfile${NC}"
    exit 1
fi

# 检查 requirements.txt 是否存在
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}✗ 错误: 找不到 requirements.txt${NC}"
    exit 1
fi

# 显示依赖信息
echo -e "${YELLOW}检查依赖文件...${NC}"
echo -e "requirements.txt 包含 $(grep -v '^#' requirements.txt | grep -v '^$' | wc -l | tr -d ' ') 个依赖包"
echo ""

# 构建镜像
echo -e "${YELLOW}开始构建镜像...${NC}"
BUILD_CMD="docker build"

if [ "$NO_CACHE" = true ]; then
    BUILD_CMD="$BUILD_CMD --no-cache"
    echo -e "${YELLOW}使用 --no-cache 参数,将重新构建所有层${NC}"
fi

BUILD_CMD="$BUILD_CMD --pull -t ${IMAGE_NAME}:latest -t ${IMAGE_NAME}:${VERSION} ."

echo -e "${BLUE}执行命令: ${BUILD_CMD}${NC}"
echo ""

# 记录开始时间
START_TIME=$(date +%s)

# 执行构建
if eval $BUILD_CMD; then
    # 记录结束时间
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    echo ""
    echo -e "${GREEN}✓ 镜像构建成功!${NC}"
    echo -e "构建耗时: ${GREEN}${DURATION}秒${NC}"
else
    echo ""
    echo -e "${RED}✗ 镜像构建失败${NC}"
    exit 1
fi

# 显示镜像信息
echo ""
echo -e "${YELLOW}镜像信息:${NC}"
docker images | grep ${IMAGE_NAME} | head -2

# 验证镜像
echo ""
echo -e "${YELLOW}验证镜像...${NC}"

# 检查镜像是否存在
if docker images | grep -q "${IMAGE_NAME}.*latest"; then
    echo -e "${GREEN}✓ 镜像存在${NC}"
else
    echo -e "${RED}✗ 镜像不存在${NC}"
    exit 1
fi

# 检查镜像大小
IMAGE_SIZE=$(docker images ${IMAGE_NAME}:latest --format "{{.Size}}")
echo -e "镜像大小: ${GREEN}${IMAGE_SIZE}${NC}"

# 测试运行容器
echo ""
echo -e "${YELLOW}测试容器启动...${NC}"
CONTAINER_ID=$(docker run -d --rm ${IMAGE_NAME}:latest sleep 10)

if [ -n "$CONTAINER_ID" ]; then
    echo -e "${GREEN}✓ 容器启动成功${NC}"
    
    # 检查 Python 版本
    PYTHON_VERSION=$(docker exec $CONTAINER_ID python --version 2>&1)
    echo -e "Python 版本: ${GREEN}${PYTHON_VERSION}${NC}"
    
    # 检查已安装的包
    echo ""
    echo -e "${YELLOW}检查关键依赖包...${NC}"
    docker exec $CONTAINER_ID pip show fastapi langchain langchain-mcp-adapters 2>/dev/null | grep -E "Name:|Version:" || true
    
    # 停止测试容器
    docker stop $CONTAINER_ID > /dev/null 2>&1 || true
    echo -e "${GREEN}✓ 测试容器已停止${NC}"
else
    echo -e "${RED}✗ 容器启动失败${NC}"
    exit 1
fi

# 推送镜像
if [ "$PUSH" = true ]; then
    echo ""
    echo -e "${YELLOW}推送镜像到仓库...${NC}"
    
    # 推送 latest 标签
    if docker push ${IMAGE_NAME}:latest; then
        echo -e "${GREEN}✓ 推送 ${IMAGE_NAME}:latest 成功${NC}"
    else
        echo -e "${RED}✗ 推送 ${IMAGE_NAME}:latest 失败${NC}"
        exit 1
    fi
    
    # 推送版本标签
    if docker push ${IMAGE_NAME}:${VERSION}; then
        echo -e "${GREEN}✓ 推送 ${IMAGE_NAME}:${VERSION} 成功${NC}"
    else
        echo -e "${RED}✗ 推送 ${IMAGE_NAME}:${VERSION} 失败${NC}"
        exit 1
    fi
fi

# 显示使用说明
echo ""
echo -e "${BLUE}======================================"
echo "构建完成!"
echo "======================================${NC}"
echo ""
echo -e "${YELLOW}运行容器:${NC}"
echo "  docker run -p 8000:8000 --env-file .env ${IMAGE_NAME}:latest"
echo ""
echo -e "${YELLOW}使用 Docker Compose:${NC}"
echo "  docker-compose up -d"
echo ""
echo -e "${YELLOW}查看日志:${NC}"
echo "  docker logs -f <container_id>"
echo ""
echo -e "${YELLOW}进入容器:${NC}"
echo "  docker exec -it <container_id> bash"
echo ""
echo -e "${YELLOW}清理旧镜像:${NC}"
echo "  docker image prune -f"
echo ""
echo -e "${GREEN}✓ 所有操作完成!${NC}"

