"""
多智能体协作图

Planner 和 Executor 通过 LangGraph 进行协作
"""
from typing import Literal
from langgraph.graph import StateGraph, END
from src.agent.multi_agent.chat_state import ChatState
from src.agent.multi_agent.agents import PlannerAgent, ExecutorAgent
from src.agent.memory import get_memory_saver
from src.tools import get_available_tools
from src.utils import app_logger


def create_chat_graph():
    """
    创建聊天图

    工作流程:
    1. START -> planner: 规划者分析需求，决定下一步行动
    2. planner -> router: 路由决策
       - next_action == "execute" -> executor: 调用执行者
       - next_action == "respond" -> responder: 直接回答
       - next_action == "finish" -> END: 结束
    3. executor -> planner: 执行完成后返回规划者（可能需要多轮）
    4. responder -> END: 直接回答后结束

    Returns:
        编译后的图
    """
    app_logger.info("创建新的聊天图...")

    # 获取工具（包含 MCP 工具）
    tools = get_available_tools(include_mcp=True)
    app_logger.info(f"加载了 {len(tools)} 个工具（包含 MCP 工具）")

    # 创建智能体
    planner = PlannerAgent()
    executor = ExecutorAgent(tools=tools)

    # 创建图
    workflow = StateGraph(ChatState)

    # 添加节点
    workflow.add_node("planner", planner.plan)
    workflow.add_node("executor", executor.execute)
    workflow.add_node("responder", _create_responder())

    # 设置入口点
    workflow.set_entry_point("planner")

    # 添加条件边：从 planner 路由到不同节点
    workflow.add_conditional_edges(
        "planner",
        _route_after_planning,
        {
            "execute": "executor",
            "respond": "responder",
            "finish": END,
        }
    )

    # executor 执行完成后返回 planner（可能需要多轮）
    workflow.add_edge("executor", "planner")

    # responder 直接回答后结束
    workflow.add_edge("responder", END)

    # 编译图（集成记忆）
    memory_saver = get_memory_saver()
    graph = workflow.compile(checkpointer=memory_saver)

    app_logger.info("聊天图创建完成")

    return graph


def _route_after_planning(state: ChatState) -> Literal["execute", "respond", "finish"]:
    """
    规划后的路由决策

    Args:
        state: 当前状态

    Returns:
        下一个节点名称
    """
    next_action = state.get("next_action", "respond")

    app_logger.info(f"[Router] 路由决策: {next_action}")

    if next_action == "execute":
        return "execute"
    elif next_action == "finish":
        return "finish"
    else:
        return "respond"


def _create_responder():
    """
    创建响应者节点

    用于直接回答用户（不需要调用执行者）
    """
    async def respond(state: ChatState):
        """直接回答"""
        from langchain_core.messages import AIMessage

        instruction = state.get("execution_instruction", "")

        app_logger.info(f"[Responder] 直接回答: {instruction[:100]}...")

        # 将回答添加到消息历史
        return {
            "messages": [AIMessage(content=instruction)],
            "is_finished": True,
        }

    return respond


# 创建全局图实例
chat_graph = create_chat_graph()


def get_chat_graph():
    """获取聊天图实例"""
    return chat_graph

