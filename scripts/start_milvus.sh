#!/bin/bash

echo "======================================"
echo "启动 Milvus 向量数据库"
echo "======================================"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker 未安装${NC}"
    echo "请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

echo -e "${GREEN}✓ Docker 已安装${NC}"

# 检查 Docker 是否运行
if ! docker info &> /dev/null; then
    echo -e "${RED}✗ Docker 未运行${NC}"
    echo "请启动 Docker Desktop"
    exit 1
fi

echo -e "${GREEN}✓ Docker 正在运行${NC}"

# 检查 Milvus 容器是否已存在
if docker ps -a | grep -q milvus-standalone; then
    echo -e "\n${YELLOW}Milvus 容器已存在${NC}"
    
    # 检查是否正在运行
    if docker ps | grep -q milvus-standalone; then
        echo -e "${GREEN}✓ Milvus 正在运行${NC}"
        echo -e "\n${BLUE}容器信息:${NC}"
        docker ps | grep milvus-standalone
        
        echo -e "\n${YELLOW}如需重启，请先停止容器:${NC}"
        echo "  docker stop milvus-standalone"
        echo "  docker rm milvus-standalone"
        echo "  然后重新运行此脚本"
        exit 0
    else
        echo -e "${YELLOW}启动现有容器...${NC}"
        docker start milvus-standalone
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Milvus 启动成功${NC}"
        else
            echo -e "${RED}✗ Milvus 启动失败${NC}"
            exit 1
        fi
    fi
else
    echo -e "\n${YELLOW}创建 Milvus 容器...${NC}"
    
    # 创建数据目录
    mkdir -p volumes/milvus
    
    # 拉取镜像
    echo -e "\n${YELLOW}拉取 Milvus 镜像...${NC}"
    docker pull milvusdb/milvus:v2.3.3
    
    # 启动 Milvus
    echo -e "\n${YELLOW}启动 Milvus 容器...${NC}"
    docker run -d \
      --name milvus-standalone \
      -p 19530:19530 \
      -p 9091:9091 \
      -v $(pwd)/volumes/milvus:/var/lib/milvus \
      milvusdb/milvus:v2.3.3 \
      milvus run standalone
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Milvus 容器创建成功${NC}"
    else
        echo -e "${RED}✗ Milvus 容器创建失败${NC}"
        exit 1
    fi
fi

# 等待 Milvus 启动
echo -e "\n${YELLOW}等待 Milvus 启动...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:9091/healthz > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Milvus 已就绪${NC}"
        break
    fi
    echo -n "."
    sleep 2
    
    if [ $i -eq 30 ]; then
        echo -e "\n${RED}✗ Milvus 启动超时${NC}"
        echo "请查看日志: docker logs milvus-standalone"
        exit 1
    fi
done

# 显示状态
echo -e "\n${BLUE}======================================"
echo "Milvus 状态"
echo "======================================${NC}"
docker ps | grep milvus-standalone

# 测试连接
echo -e "\n${YELLOW}测试连接...${NC}"
if curl -s http://localhost:9091/healthz | grep -q "OK"; then
    echo -e "${GREEN}✓ 健康检查通过${NC}"
else
    echo -e "${RED}✗ 健康检查失败${NC}"
fi

# 显示信息
echo -e "\n${BLUE}======================================"
echo "Milvus 信息"
echo "======================================${NC}"
echo -e "主机: ${GREEN}localhost${NC}"
echo -e "端口: ${GREEN}19530${NC}"
echo -e "健康检查: ${GREEN}http://localhost:9091/healthz${NC}"
echo -e "指标: ${GREEN}http://localhost:9091/metrics${NC}"

echo -e "\n${BLUE}======================================"
echo "常用命令"
echo "======================================${NC}"
echo "查看日志: docker logs -f milvus-standalone"
echo "停止服务: docker stop milvus-standalone"
echo "启动服务: docker start milvus-standalone"
echo "删除容器: docker rm -f milvus-standalone"
echo "进入容器: docker exec -it milvus-standalone bash"

echo -e "\n${BLUE}======================================"
echo "下一步"
echo "======================================${NC}"
echo "1. 配置 .env 文件:"
echo "   ENABLE_RAG_TOOL=true"
echo "   RAG_MILVUS_HOST=localhost"
echo "   RAG_MILVUS_PORT=19530"
echo ""
echo "2. 安装依赖:"
echo "   pip install pymilvus langchain-milvus"
echo ""
echo "3. 启动智能体:"
echo "   python run.py"
echo ""
echo "4. 测试知识库:"
echo "   bash scripts/test_rag.sh"
echo ""

echo -e "${GREEN}✓ Milvus 启动完成!${NC}"

