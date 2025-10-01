"""
LangGraph图定义
"""
from langgraph.graph import StateGraph, END
from src.utils import app_logger
from .state import AgentState
from .nodes import entry_node, llm_node, output_node, should_continue


def create_agent_graph():
    """创建智能体图"""
    app_logger.info("创建智能体图")
    
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
    
    # 编译图
    app = workflow.compile()
    
    app_logger.info("智能体图创建完成")
    return app


# 创建全局智能体实例
agent_graph = create_agent_graph()

