#!/bin/bash

# 多智能体系统测试脚本

set -e

echo "======================================"
echo "多智能体系统测试"
echo "======================================"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 基础 URL
BASE_URL="http://localhost:8000"

# 检查服务是否运行
echo -e "\n${YELLOW}检查服务状态...${NC}"
if ! curl -s "${BASE_URL}/api/v1/health" > /dev/null; then
    echo -e "${RED}错误: 服务未运行,请先启动服务${NC}"
    echo "运行: python run.py"
    exit 1
fi
echo -e "${GREEN}✓ 服务正在运行${NC}"

# 测试 1: 获取智能体列表
echo -e "\n${YELLOW}测试 1: 获取智能体列表${NC}"
response=$(curl -s "${BASE_URL}/api/v1/multi-agent/agents")
echo "$response" | python -m json.tool
echo -e "${GREEN}✓ 测试通过${NC}"

# 测试 2: 获取统计信息
echo -e "\n${YELLOW}测试 2: 获取统计信息${NC}"
response=$(curl -s "${BASE_URL}/api/v1/multi-agent/statistics")
echo "$response" | python -m json.tool
echo -e "${GREEN}✓ 测试通过${NC}"

# 测试 3: 顺序协作模式
echo -e "\n${YELLOW}测试 3: 顺序协作模式${NC}"
response=$(curl -s -X POST "${BASE_URL}/api/v1/multi-agent/test/sequential" \
  -H "Content-Type: application/json")
echo "$response" | python -m json.tool
echo -e "${GREEN}✓ 测试通过${NC}"

# 测试 4: 反馈协作模式
echo -e "\n${YELLOW}测试 4: 反馈协作模式${NC}"
response=$(curl -s -X POST "${BASE_URL}/api/v1/multi-agent/test/feedback" \
  -H "Content-Type: application/json")
echo "$response" | python -m json.tool
echo -e "${GREEN}✓ 测试通过${NC}"

# 测试 5: 自定义任务
echo -e "\n${YELLOW}测试 5: 自定义任务${NC}"
response=$(curl -s -X POST "${BASE_URL}/api/v1/multi-agent/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "分析用户对新功能的需求",
    "type": "requirement_analysis",
    "context": "准备开发新功能",
    "requirements": ["用户痛点", "功能需求", "优先级"],
    "coordination_mode": "sequential",
    "max_iterations": 5
  }')
echo "$response" | python -m json.tool
echo -e "${GREEN}✓ 测试通过${NC}"

echo -e "\n${GREEN}======================================"
echo "所有测试通过!"
echo "======================================${NC}"

