# 多智能体系统快速开始

## 🎯 5 分钟快速体验

### 1. 启动服务

```bash
# 启动应用
python run.py
```

等待服务启动,看到以下日志表示成功:

```
✓ 已注册 5 个智能体
启动 cus-ai-agent API v1.0.0
API地址: http://localhost:8000
文档地址: http://localhost:8000/docs
```

### 2. 测试 API

打开浏览器访问: http://localhost:8000/docs

或使用 curl 测试:

```bash
# 获取智能体列表
curl http://localhost:8000/api/v1/multi-agent/agents | python -m json.tool

# 测试顺序协作模式
curl -X POST http://localhost:8000/api/v1/multi-agent/test/sequential | python -m json.tool
```

### 3. 运行示例

```bash
# 运行交互式示例
python examples/multi_agent_example.py

# 选择示例 1: 顺序协作模式
```

---

## 📚 核心概念

### 智能体类型

| 智能体 | 职责 | 适用场景 |
|--------|------|----------|
| **AnalystAgent** | 需求分析、数据分析 | 需求分析、市场调研 |
| **PlannerAgent** | 任务分解、策略规划 | 项目规划、任务分解 |
| **ExecutorAgent** | 任务执行、工具调用 | 代码生成、API 调用 |
| **ReviewerAgent** | 结果验证、质量检查 | 代码审查、质量检查 |
| **ResearcherAgent** | 深度研究、报告生成 | 技术调研、知识整合 |

### 协作模式

| 模式 | 说明 | 使用场景 |
|------|------|----------|
| **Sequential** | 顺序执行 | 有明确执行顺序的任务 |
| **Parallel** | 并行执行 | 独立子任务的并行处理 |
| **Hierarchical** | 层级协作 | 复杂的多层次任务 |
| **Feedback** | 反馈循环 | 需要迭代优化的任务 |

---

## 💡 使用示例

### 示例 1: 产品需求分析(顺序模式)

```bash
curl -X POST http://localhost:8000/api/v1/multi-agent/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "分析用户对移动支付功能的需求",
    "type": "requirement_analysis",
    "requirements": ["用户痛点", "功能需求", "优先级"],
    "coordination_mode": "sequential"
  }'
```

**执行流程**:
```
Analyst(分析需求) → Planner(制定计划) → Executor(执行分析) → Reviewer(评审结果)
```

### 示例 2: 代码生成与优化(反馈模式)

```bash
curl -X POST http://localhost:8000/api/v1/multi-agent/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "生成一个快速排序算法实现",
    "type": "code_generation",
    "requirements": ["Python实现", "包含注释", "包含测试"],
    "coordination_mode": "feedback",
    "max_feedback_rounds": 3
  }'
```

**执行流程**:
```
Executor(生成代码) → Reviewer(评审) → [如果不通过] → Executor(改进) → ...
```

### 示例 3: 技术调研(研究模式)

```bash
curl -X POST http://localhost:8000/api/v1/multi-agent/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "调研 LangGraph 多智能体框架",
    "type": "research",
    "requirements": ["技术原理", "应用场景", "最佳实践"],
    "coordination_mode": "sequential"
  }'
```

---

## 🔧 Python SDK 使用

### 直接使用智能体

```python
from src.agent.multi_agent.agents import AnalystAgent, PlannerAgent

# 创建智能体
analyst = AnalystAgent()

# 分析需求
result = await analyst.analyze_requirements(
    "用户希望有一个简单易用的任务管理工具"
)

print(result)
```

### 使用多智能体图

```python
from src.agent.multi_agent.multi_agent_state import create_initial_state
from src.agent.multi_agent.multi_agent_graph import multi_agent_graph

# 创建任务
task = {
    "description": "分析并制定产品计划",
    "type": "planning"
}

# 创建初始状态
initial_state = create_initial_state(
    task=task,
    coordination_mode="sequential"
)

# 执行
result = await multi_agent_graph.ainvoke(initial_state)

print(result["final_result"])
```

---

## 📊 API 响应示例

### 成功响应

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task": {
      "description": "分析用户需求",
      "type": "requirement_analysis"
    },
    "coordination_mode": "sequential",
    "agents_involved": [
      "analyst_001",
      "planner_001",
      "executor_001",
      "reviewer_001"
    ],
    "final_result": {
      "summary": "需求分析完成",
      "details": {...}
    },
    "is_finished": true,
    "error": null
  }
}
```

### 错误响应

```json
{
  "code": 500,
  "message": "执行失败",
  "data": {
    "error": "智能体执行超时",
    "is_finished": false
  }
}
```

---

## 🎨 架构图

```
┌─────────────────────────────────────────┐
│         FastAPI Application              │
├─────────────────────────────────────────┤
│       Multi-Agent REST API               │
├─────────────────────────────────────────┤
│       Multi-Agent Graph                  │
│       (LangGraph StateGraph)             │
├─────────────────────────────────────────┤
│       Agent Coordinator                  │
├─────────────────────────────────────────┤
│  Analyst │ Planner │ Executor │ ...     │
├─────────────────────────────────────────┤
│       LLM (OpenAI-compatible)            │
└─────────────────────────────────────────┘
```

---

## 🚀 下一步

1. **阅读详细文档**
   - [架构设计](./multi-agent-architecture.md)
   - [使用指南](./multi-agent-usage-guide.md)
   - [实现总结](./multi-agent-implementation-summary.md)

2. **运行更多示例**
   ```bash
   python examples/multi_agent_example.py
   ```

3. **自定义智能体**
   - 继承 `BaseAgent` 类
   - 实现 `_define_capabilities()` 方法
   - 实现 `_get_default_system_prompt()` 方法
   - 实现 `process()` 方法

4. **集成到你的应用**
   ```python
   from src.agent.multi_agent.multi_agent_graph import multi_agent_graph
   
   # 在你的代码中使用
   result = await multi_agent_graph.ainvoke(initial_state)
   ```

---

## 📞 获取帮助

- 查看 [API 文档](http://localhost:8000/docs)
- 阅读 [使用指南](./multi-agent-usage-guide.md)
- 查看 [示例代码](../../examples/multi_agent_example.py)

---

**祝你使用愉快! 🎉**

