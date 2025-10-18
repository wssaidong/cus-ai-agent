"""
LangGraph Studio 专用 Graph 构建器 - 集成 InMemorySaver 记忆功能

此模块为 LangGraph Studio UI 提供可视化和调试支持。
与 src/agent/graph.py 的主要区别:
1. 集成 InMemorySaver 用于本地开发调试
2. 导出 graph 变量供 Studio 加载
3. 优化了节点命名以提升可视化效果
4. 支持状态持久化和回溯
"""
from langgraph.graph import StateGraph, END
from src.utils import app_logger
from src.agent.state import AgentState
from src.agent.nodes import entry_node, llm_node, output_node
from src.agent.memory import get_memory_saver


def create_studio_graph(enable_memory: bool = True):
    """
    创建支持 LangGraph Studio 的智能体图

    特性:
    - 集成 InMemorySaver 用于本地开发调试
    - 支持 Studio UI 可视化和调试
    - 支持状态回溯和检查
    - 支持记忆功能

    Args:
        enable_memory: 是否启用 InMemorySaver 记忆功能

    Returns:
        CompiledGraph: 编译后的图实例
    """
    app_logger.info(f"创建 LangGraph Studio 智能体图 (记忆功能: {'启用' if enable_memory else '禁用'})")

    # 创建状态图
    workflow = StateGraph(AgentState)

    # 添加节点
    # 节点名称会在 Studio UI 中显示,使用清晰的命名
    workflow.add_node("entry", entry_node)
    workflow.add_node("llm", llm_node)
    workflow.add_node("output", output_node)

    # 设置入口点
    workflow.set_entry_point("entry")

    # 添加边 - 定义执行流程
    workflow.add_edge("entry", "llm")
    workflow.add_edge("llm", "output")
    workflow.add_edge("output", END)

    # 编译图 - 集成 InMemorySaver
    if enable_memory:
        memory_saver = get_memory_saver()
        app = workflow.compile(checkpointer=memory_saver)
        app_logger.info("LangGraph Studio 智能体图创建完成 (已集成 InMemorySaver)")
    else:
        app = workflow.compile()
        app_logger.info("LangGraph Studio 智能体图创建完成 (未启用记忆功能)")

    app_logger.info("可通过 'langgraph dev' 启动 Studio UI")

    return app


# 导出 graph 供 LangGraph Studio 使用
# 变量名必须与 langgraph.json 中配置的一致
graph = create_studio_graph(enable_memory=True)

