"""
LangGraph Studio 专用 Graph 构建器 - 多智能体架构

此模块为 LangGraph Studio UI 提供可视化和调试支持。
使用 Supervisor 模式多智能体架构。
"""
from src.utils import app_logger
from src.agent.multi_agent.chat_graph import get_chat_graph


def create_studio_graph():
    """
    创建支持 LangGraph Studio 的多智能体图

    特性:
    - 使用 Supervisor 模式架构
    - 集成 InMemorySaver 用于本地开发调试
    - 支持 Studio UI 可视化和调试
    - 支持状态回溯和检查

    Returns:
        CompiledGraph: 编译后的图实例
    """
    app_logger.info("创建 LangGraph Studio 多智能体图")

    # 获取多智能体聊天图
    chat_graph = get_chat_graph()

    app_logger.info("LangGraph Studio 多智能体图创建完成")
    app_logger.info("可通过 'langgraph dev' 启动 Studio UI")

    return chat_graph


# 导出 graph 供 LangGraph Studio 使用
# 变量名必须与 langgraph.json 中配置的一致
graph = create_studio_graph()

