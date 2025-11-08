"""
LangGraph Studio 专用 Graph 构建器 - 多智能体架构

此模块为 LangGraph Studio UI 提供可视化和调试支持。
使用 Supervisor 模式多智能体架构。

注意:
- LangGraph Studio 在导入时会立即访问 graph 变量
- 此时 MCP 工具可能还未加载，所以 ExecutionAgent 可能没有 MCP 工具
- 如需完整的 MCP 工具支持，建议先启动 FastAPI 应用加载 MCP 工具
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

    注意:
    - 延迟初始化确保在 MCP 工具加载后才创建图
    - 首次调用时才会真正创建图实例

    Returns:
        CompiledGraph: 编译后的图实例
    """
    app_logger.info("创建 LangGraph Studio 多智能体图")

    # 获取多智能体聊天图（延迟初始化）
    chat_graph = get_chat_graph()

    app_logger.info("LangGraph Studio 多智能体图创建完成")
    app_logger.info("可通过 'langgraph dev' 启动 Studio UI")

    return chat_graph


# 导出 graph 供 LangGraph Studio 使用
# 变量名必须与 langgraph.json 中配置的一致
# 注意: 这里会立即调用 create_studio_graph()，触发图的创建
# 如果需要 MCP 工具，建议先启动 FastAPI 应用
graph = create_studio_graph()

