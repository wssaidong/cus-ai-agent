"""
LangGraph图定义 - 集成 InMemorySaver 记忆功能
"""
from langgraph.graph import StateGraph, END
from src.utils import app_logger
from .state import AgentState
from .nodes import entry_node, llm_node, output_node, should_continue
from .memory import get_memory_saver


def create_agent_graph(enable_memory: bool = True):
    """
    创建智能体图

    Args:
        enable_memory: 是否启用记忆功能（使用 InMemorySaver）

    Returns:
        编译后的图实例
    """
    app_logger.info(f"创建智能体图 (记忆功能: {'启用' if enable_memory else '禁用'})")

    # 创建状态图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("entry", entry_node)
    workflow.add_node("llm", llm_node)
    workflow.add_node("output", output_node)

    # 设置入口点
    workflow.set_entry_point("entry")

    # 添加边
    workflow.add_edge("entry", "llm")
    workflow.add_edge("llm", "output")
    workflow.add_edge("output", END)

    # 编译图 - 集成 InMemorySaver
    if enable_memory:
        memory_saver = get_memory_saver()
        app = workflow.compile(checkpointer=memory_saver)
        app_logger.info("智能体图创建完成 (已集成 InMemorySaver)")
    else:
        app = workflow.compile()
        app_logger.info("智能体图创建完成 (未启用记忆功能)")

    return app


# 创建全局智能体实例（默认启用记忆功能）
agent_graph = create_agent_graph(enable_memory=True)

