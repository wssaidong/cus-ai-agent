# 多智能体系统使用指南

## 📋 概述

本文档介绍如何使用多智能体系统完成复杂任务。

---

## 🚀 快速开始

### 1. 启动服务

```bash
# 启动应用
python run.py

# 或使用脚本
./scripts/start.sh
```

服务启动后,访问 http://localhost:8000/docs 查看 API 文档。

### 2. 基本使用

#### 执行简单任务(顺序模式)

```bash
curl -X POST "http://localhost:8000/api/v1/multi-agent/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "分析并制定一个产品发布计划",
    "type": "planning",
    "context": "新产品即将上市",
    "requirements": ["市场分析", "时间规划", "资源分配"],
    "coordination_mode": "sequential"
  }'
```

#### 执行需要反馈的任务(反馈模式)

```bash
curl -X POST "http://localhost:8000/api/v1/multi-agent/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "撰写一篇技术博客文章",
    "type": "content_generation",
    "requirements": ["技术准确", "易于理解", "结构清晰"],
    "coordination_mode": "feedback",
    "max_feedback_rounds": 3
  }'
```

---

## 🤖 智能体介绍

### 1. AnalystAgent (分析师)

**职责**: 信息收集、数据分析、洞察提取

**适用场景**:
- 需求分析
- 市场调研
- 数据分析
- 趋势识别

**示例**:
```python
from src.agent.multi_agent.agents import AnalystAgent

analyst = AnalystAgent()
result = await analyst.analyze_requirements("分析用户对新功能的需求")
```

### 2. PlannerAgent (规划师)

**职责**: 任务分解、策略制定、计划优化

**适用场景**:
- 项目规划
- 任务分解
- 策略制定
- 资源分配

**示例**:
```python
from src.agent.multi_agent.agents import PlannerAgent

planner = PlannerAgent()
plan = await planner.decompose_task("开发一个新功能")
```

### 3. ExecutorAgent (执行者)

**职责**: 具体任务执行、工具调用、结果生成

**适用场景**:
- 代码生成
- 文档撰写
- API 调用
- 数据处理

**示例**:
```python
from src.agent.multi_agent.agents import ExecutorAgent

executor = ExecutorAgent()
result = await executor.execute_with_tools("生成一个 Python 函数")
```

### 4. ReviewerAgent (评审者)

**职责**: 结果验证、质量检查、改进建议

**适用场景**:
- 代码审查
- 文档审核
- 质量检查
- 结果验证

**示例**:
```python
from src.agent.multi_agent.agents import ReviewerAgent

reviewer = ReviewerAgent()
review = await reviewer.review_quality(execution_result)
```

### 5. ResearcherAgent (研究员)

**职责**: 深度研究、知识整合、报告生成

**适用场景**:
- 技术调研
- 竞品分析
- 知识整合
- 报告生成

**示例**:
```python
from src.agent.multi_agent.agents import ResearcherAgent

researcher = ResearcherAgent()
report = await researcher.research_topic("人工智能最新进展")
```

---

## 🔄 协作模式

### 1. 顺序协作 (Sequential)

智能体按顺序依次执行,适合有明确执行顺序的任务。

**执行流程**: Analyst → Planner → Executor → Reviewer

**使用场景**:
- 项目规划
- 产品开发
- 内容创作

**示例**:
```json
{
  "description": "开发一个新功能",
  "coordination_mode": "sequential"
}
```

### 2. 并行协作 (Parallel)

多个智能体同时执行不同的子任务,适合独立子任务。

**使用场景**:
- 多维度分析
- 并行处理
- 快速执行

**示例**:
```json
{
  "description": "全面分析市场情况",
  "coordination_mode": "parallel",
  "task_plan": [
    {"description": "分析竞品", "agent_type": "analyst"},
    {"description": "分析用户", "agent_type": "analyst"},
    {"description": "分析趋势", "agent_type": "researcher"}
  ]
}
```

### 3. 层级协作 (Hierarchical)

协调者分配任务给下级智能体,适合复杂的多层次任务。

**使用场景**:
- 大型项目
- 复杂任务
- 多层管理

**示例**:
```json
{
  "description": "完整的产品开发流程",
  "coordination_mode": "hierarchical"
}
```

### 4. 反馈协作 (Feedback Loop)

智能体之间形成反馈循环,不断优化结果。

**执行流程**: Executor → Reviewer → (如果不通过) → Executor → ...

**使用场景**:
- 代码生成
- 文档撰写
- 质量优化

**示例**:
```json
{
  "description": "生成高质量代码",
  "coordination_mode": "feedback",
  "max_feedback_rounds": 3
}
```

---

## 📝 使用示例

### 示例 1: 产品需求分析

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/multi-agent/tasks",
    json={
        "description": "分析用户对移动支付功能的需求",
        "type": "requirement_analysis",
        "context": "准备开发移动支付功能",
        "requirements": [
            "用户痛点分析",
            "功能需求提取",
            "优先级排序"
        ],
        "coordination_mode": "sequential"
    }
)

result = response.json()
print(result["data"]["final_result"])
```

### 示例 2: 代码生成与优化

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/multi-agent/tasks",
    json={
        "description": "生成一个高效的排序算法实现",
        "type": "code_generation",
        "requirements": [
            "时间复杂度 O(n log n)",
            "代码清晰易读",
            "包含注释和测试"
        ],
        "coordination_mode": "feedback",
        "max_feedback_rounds": 2
    }
)

result = response.json()
print(result["data"]["final_result"])
```

### 示例 3: 技术调研报告

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/multi-agent/tasks",
    json={
        "description": "调研并撰写关于 LangGraph 的技术报告",
        "type": "research",
        "requirements": [
            "技术原理",
            "应用场景",
            "最佳实践",
            "案例分析"
        ],
        "coordination_mode": "sequential"
    }
)

result = response.json()
print(result["data"]["final_result"])
```

---

## 🔍 API 接口

### 1. 执行多智能体任务

**端点**: `POST /api/v1/multi-agent/tasks`

**请求体**:
```json
{
  "description": "任务描述",
  "type": "任务类型",
  "context": "上下文信息",
  "requirements": ["需求1", "需求2"],
  "coordination_mode": "sequential",
  "session_id": "可选的会话ID",
  "max_iterations": 10,
  "max_feedback_rounds": 3
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task": {...},
    "coordination_mode": "sequential",
    "agents_involved": ["analyst_001", "planner_001", ...],
    "final_result": {...},
    "is_finished": true,
    "error": null
  }
}
```

### 2. 获取智能体列表

**端点**: `GET /api/v1/multi-agent/agents`

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "agents": [
      {
        "agent_id": "analyst_001",
        "agent_type": "analyst",
        "name": "分析师",
        "description": "负责信息收集、数据分析和洞察提取",
        "status": "idle",
        "capabilities": [...]
      }
    ],
    "total": 5
  }
}
```

### 3. 获取智能体详情

**端点**: `GET /api/v1/multi-agent/agents/{agent_id}`

### 4. 获取统计信息

**端点**: `GET /api/v1/multi-agent/statistics`

---

## 🎯 最佳实践

### 1. 选择合适的协作模式

- **顺序模式**: 任务有明确的执行顺序
- **并行模式**: 子任务相互独立
- **层级模式**: 复杂的多层次任务
- **反馈模式**: 需要迭代优化的任务

### 2. 设置合理的参数

```python
{
    "max_iterations": 10,  # 防止无限循环
    "max_feedback_rounds": 3,  # 控制反馈次数
    "session_id": "unique_id"  # 启用会话记忆
}
```

### 3. 提供清晰的需求

```python
{
    "description": "具体、清晰的任务描述",
    "requirements": [
        "明确的需求1",
        "明确的需求2"
    ],
    "context": "相关的上下文信息"
}
```

### 4. 处理错误

```python
try:
    result = await execute_task(request)
    if result.get("error"):
        # 处理错误
        handle_error(result["error"])
except Exception as e:
    # 处理异常
    log_exception(e)
```

---

## 🐛 故障排查

### 问题 1: 智能体未注册

**症状**: 提示"未找到智能体"

**解决方案**:
```python
from src.agent.multi_agent.multi_agent_graph import initialize_agents
from src.agent.multi_agent.agent_registry import agent_registry

# 重新初始化智能体
initialize_agents(agent_registry)
```

### 问题 2: 任务执行超时

**症状**: 任务长时间未完成

**解决方案**:
- 减少 `max_iterations`
- 简化任务描述
- 检查智能体状态

### 问题 3: 反馈循环不收敛

**症状**: 达到最大反馈轮次仍未通过

**解决方案**:
- 降低评审标准
- 增加 `max_feedback_rounds`
- 检查 Reviewer 的提示词

---

## 📚 更多资源

- [多智能体架构设计](./multi-agent-architecture.md)
- [API 参考文档](../api-reference.md)
- [开发指南](../development-guide.md)

