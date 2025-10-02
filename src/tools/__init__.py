"""工具模块"""
from typing import List
from langchain.tools import BaseTool
from src.config import settings
from src.utils import app_logger
from .database import DatabaseQueryTool, DatabaseInfoTool
from .api_caller import APICallTool
from .custom_tools import CalculatorTool, TextProcessTool


def get_available_tools() -> List[BaseTool]:
    """获取可用的工具列表"""
    tools = []

    # 数据库工具
    if settings.enable_database_tool and settings.database_url:
        tools.append(DatabaseQueryTool(database_url=settings.database_url))
        tools.append(DatabaseInfoTool(database_url=settings.database_url))

    # API调用工具
    if settings.enable_api_tool:
        tools.append(APICallTool(timeout=settings.timeout_seconds))

    # 自定义工具（默认启用）
    tools.append(CalculatorTool())
    tools.append(TextProcessTool())

    # RAG知识库工具
    if settings.enable_rag_tool:
        try:
            from .rag_tool import create_rag_search_tool
            rag_tool = create_rag_search_tool()
            tools.append(rag_tool)
            app_logger.info("成功加载 RAG 知识库工具")
        except Exception as e:
            app_logger.error(f"加载 RAG 工具失败: {str(e)}")

    # MCP工具（动态加载）
    if settings.enable_mcp_tools and settings.mcp_server_url:
        try:
            from .mcp_client import create_mcp_tools_sync

            # 使用较短的超时时间避免启动卡住
            mcp_tools = create_mcp_tools_sync(
                server_url=settings.mcp_server_url,
                timeout=min(settings.mcp_timeout, 5)  # 限制最大超时时间为 5 秒
            )

            if mcp_tools:
                tools.extend(mcp_tools)
                app_logger.info(f"成功加载 {len(mcp_tools)} 个MCP工具")
            else:
                app_logger.warning("MCP 服务器未返回任何工具")

        except Exception as e:
            app_logger.error(f"加载MCP工具失败: {str(e)}")
            app_logger.info("继续启动，但 MCP 工具不可用")

    return tools


__all__ = [
    "get_available_tools",
    "DatabaseQueryTool",
    "DatabaseInfoTool",
    "APICallTool",
    "CalculatorTool",
    "TextProcessTool",
]

