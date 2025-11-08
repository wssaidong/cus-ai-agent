"""
多智能体协作图 - Supervisor 模式

Supervisor 协调多个专业化的 Worker Agents 完成任务
"""
from typing import Literal
from langgraph.graph import StateGraph, END
from src.agent.multi_agent.chat_state import ChatState
from src.agent.multi_agent.agents.supervisor import SupervisorAgent
from src.agent.multi_agent.agents.search_agent import SearchAgent
from src.agent.multi_agent.agents.write_agent import WriteAgent
from src.agent.multi_agent.agents.analysis_agent import AnalysisAgent
from src.agent.multi_agent.agents.execution_agent import ExecutionAgent
from src.agent.multi_agent.agents.quality_agent import QualityAgent
from src.agent.memory import get_memory_saver
from src.tools import get_available_tools
from src.utils import app_logger


def create_chat_graph():
    """
    创建聊天图 - Supervisor 模式

    工作流程:
    1. START -> supervisor: Supervisor 分析任务，决定调用哪个 Worker
    2. supervisor -> router: 路由决策
       - next_agent == "search_agent" -> search_agent: 搜索智能体
       - next_agent == "write_agent" -> write_agent: 写入智能体
       - next_agent == "analysis_agent" -> analysis_agent: 分析智能体
       - next_agent == "execution_agent" -> execution_agent: 执行智能体
       - next_agent == "respond" -> responder: 直接回答
       - next_agent == "finish" -> END: 结束
    3. worker_agents -> END: Worker 完成后直接结束（避免无限循环）
    4. responder -> END: 直接回答后结束

    Supervisor 模式优势:
    - 中央协调：Supervisor 统一管理所有 Worker
    - 职责分离：每个 Worker 专注于特定领域
    - 易于扩展：添加新 Worker 无需修改现有逻辑
    - 灵活调度：根据任务类型动态选择最合适的 Worker

    Returns:
        编译后的图
    """
    app_logger.info("创建 Supervisor 模式聊天图...")

    # 获取工具（包含 MCP 工具）
    tools = get_available_tools(include_mcp=True)
    app_logger.info(f"加载了 {len(tools)} 个工具（包含 MCP 工具）")

    # 创建 Worker Agents
    search_agent = SearchAgent(tools=tools)
    write_agent = WriteAgent(tools=tools)
    analysis_agent = AnalysisAgent(tools=tools)
    execution_agent = ExecutionAgent(tools=tools)
    quality_agent = QualityAgent()  # 质量优化智能体不需要工具

    # 收集每个 Worker 的工具信息
    worker_tools = {
        "search_agent": search_agent.tools,
        "write_agent": write_agent.tools,
        "analysis_agent": analysis_agent.tools,
        "execution_agent": execution_agent.tools,
        "quality_agent": [],  # 质量智能体不使用工具
    }

    app_logger.info("Worker 工具分配:")
    for worker_name, worker_tool_list in worker_tools.items():
        app_logger.info(f"  - {worker_name}: {len(worker_tool_list)} 个工具")

    # 创建 Supervisor（传递工具信息）
    worker_names = ["search_agent", "write_agent", "analysis_agent", "execution_agent", "quality_agent"]
    supervisor = SupervisorAgent(
        worker_names=worker_names,
        worker_tools=worker_tools  # 传递工具信息
    )

    # 创建图
    workflow = StateGraph(ChatState)

    # 添加节点
    workflow.add_node("supervisor", supervisor.supervise)
    workflow.add_node("search_agent", search_agent.execute)
    workflow.add_node("write_agent", write_agent.execute)
    workflow.add_node("analysis_agent", analysis_agent.execute)
    workflow.add_node("execution_agent", execution_agent.execute)
    workflow.add_node("quality_agent", quality_agent)
    workflow.add_node("responder", _create_responder())

    # 设置入口点
    workflow.set_entry_point("supervisor")

    # 添加条件边：从 supervisor 路由到不同节点
    workflow.add_conditional_edges(
        "supervisor",
        _route_after_supervision,
        {
            "search_agent": "search_agent",
            "write_agent": "write_agent",
            "analysis_agent": "analysis_agent",
            "execution_agent": "execution_agent",
            "quality_agent": "quality_agent",
            "respond": "responder",
            "finish": END,
        }
    )

    # Worker Agents 执行完成后直接结束（避免无限循环）
    # 修复：之前 Worker 完成后返回 supervisor 导致不断重复调用
    workflow.add_edge("search_agent", END)
    workflow.add_edge("write_agent", END)
    workflow.add_edge("analysis_agent", END)
    workflow.add_edge("execution_agent", END)
    workflow.add_edge("quality_agent", END)

    # responder 直接回答后结束
    workflow.add_edge("responder", END)

    # 编译图（集成记忆）
    memory_saver = get_memory_saver()
    graph = workflow.compile(checkpointer=memory_saver)

    app_logger.info("Supervisor 模式聊天图创建完成")
    app_logger.info(f"Supervisor 管理 {len(worker_names)} 个 Worker Agents: {', '.join(worker_names)}")

    return graph


def _route_after_supervision(state: ChatState) -> Literal["search_agent", "write_agent", "analysis_agent", "execution_agent", "quality_agent", "respond", "finish"]:
    """
    Supervisor 决策后的路由

    Args:
        state: 当前状态

    Returns:
        下一个节点名称
    """
    next_agent = state.get("next_agent", "respond")

    app_logger.info(f"[Router] Supervisor 路由决策: {next_agent}")

    # 验证 next_agent 是否有效
    valid_agents = ["search_agent", "write_agent", "analysis_agent", "execution_agent", "quality_agent", "respond", "finish"]
    if next_agent not in valid_agents:
        app_logger.warning(f"[Router] 无效的 next_agent: {next_agent}，默认使用 respond")
        return "respond"

    return next_agent


def _create_responder():
    """
    创建响应者节点

    用于直接回答用户（不需要调用 Worker Agent）
    """
    async def respond(state: ChatState):
        """直接回答"""
        from langchain_core.messages import AIMessage

        task_instruction = state.get("task_instruction", "")

        app_logger.info(f"[Responder] 直接回答: {task_instruction[:100]}...")

        # 将回答添加到消息历史
        return {
            "messages": [AIMessage(content=task_instruction)],
            "is_finished": True,
        }

    return respond


# 全局图实例（延迟初始化）
_chat_graph = None


def get_chat_graph():
    """
    获取聊天图实例（延迟初始化）

    延迟初始化确保在 MCP 工具加载后才创建图，
    这样 ExecutionAgent 才能获取到所有 MCP 工具
    """
    global _chat_graph

    if _chat_graph is None:
        app_logger.info("首次调用，创建聊天图...")
        _chat_graph = create_chat_graph()

    return _chat_graph

