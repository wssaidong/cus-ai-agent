"""
LangGraph Studio 专用 Graph 构建器

此模块为 LangGraph Studio UI 提供可视化和调试支持。
与 src/agent/graph.py 的主要区别:
1. 不使用自定义 checkpointer,由 LangGraph API 平台自动处理持久化
2. 导出 graph 变量供 Studio 加载
3. 优化了节点命名以提升可视化效果
"""
from langgraph.graph import StateGraph, END
from src.utils import app_logger
from src.agent.state import AgentState
from src.agent.nodes import entry_node, llm_node, output_node


def create_studio_graph():
    """
    创建支持 LangGraph Studio 的智能体图

    特性:
    - 由 LangGraph API 平台自动处理状态持久化
    - 支持 Studio UI 可视化和调试
    - 支持状态回溯和检查

    Returns:
        CompiledGraph: 编译后的图实例
    """
    app_logger.info("创建 LangGraph Studio 智能体图")

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

    # 编译图 - 不使用自定义 checkpointer
    # LangGraph API 平台会自动处理持久化
    # 如需自定义数据库,可通过 POSTGRES_URI 环境变量配置
    app = workflow.compile()

    app_logger.info("LangGraph Studio 智能体图创建完成")
    app_logger.info("可通过 'langgraph dev' 启动 Studio UI")

    return app


# 导出 graph 供 LangGraph Studio 使用
# 变量名必须与 langgraph.json 中配置的一致
graph = create_studio_graph()

