#!/bin/bash

# 智能体成熟度测试运行脚本
# 用法: ./scripts/run_maturity_test.sh [URL] [OUTPUT_FILE]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
DEFAULT_URL="http://10.225.8.186/api/v1"
DEFAULT_OUTPUT="maturity_report.json"

# 获取参数
AGENT_URL=${1:-$DEFAULT_URL}
OUTPUT_FILE=${2:-$DEFAULT_OUTPUT}

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}智能体成熟度验证测试${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "${YELLOW}配置信息:${NC}"
echo -e "  智能体地址: ${AGENT_URL}"
echo -e "  报告输出: ${OUTPUT_FILE}"
echo ""

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到Python3${NC}"
    exit 1
fi

# 检查依赖
echo -e "${YELLOW}检查依赖...${NC}"
if ! python3 -c "import requests" 2>/dev/null; then
    echo -e "${YELLOW}安装requests库...${NC}"
    pip3 install requests
fi

# 检查服务是否可用
echo -e "${YELLOW}检查服务可用性...${NC}"
if curl -s -f "${AGENT_URL}/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 服务可用${NC}"
else
    echo -e "${RED}✗ 服务不可用: ${AGENT_URL}${NC}"
    echo -e "${YELLOW}请检查:${NC}"
    echo -e "  1. 服务是否启动"
    echo -e "  2. URL是否正确"
    echo -e "  3. 网络连接是否正常"
    exit 1
fi

# 运行测试
echo ""
echo -e "${YELLOW}开始运行测试...${NC}"
echo ""

python3 tests/test_agent_maturity.py --url "${AGENT_URL}" --output "${OUTPUT_FILE}"

TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ 测试完成，智能体成熟度达标 (≥60分)${NC}"
else
    echo -e "${RED}✗ 测试完成，智能体成熟度不达标 (<60分)${NC}"
fi

echo ""
echo -e "${BLUE}报告已保存到: ${OUTPUT_FILE}${NC}"
echo ""

exit $TEST_EXIT_CODE

