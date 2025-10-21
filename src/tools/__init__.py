"""工具模块"""
from typing import List
from langchain.tools import BaseTool
from src.config import settings
from src.utils import app_logger
from .knowledge_write_tool import KnowledgeBaseWriteTool, KnowledgeBaseUpdateTool

# 全局 MCP 工具缓存
_mcp_tools_cache: List[BaseTool] = []


async def load_mcp_tools_async() -> List[BaseTool]:
    """异步加载 MCP 工具"""
    global _mcp_tools_cache

    if _mcp_tools_cache:
        app_logger.info(f"使用缓存的 {len(_mcp_tools_cache)} 个 MCP 工具")
        return _mcp_tools_cache

    try:
        from .mcp_adapter import create_mcp_tools_async

        mcp_tools = await create_mcp_tools_async()

        if mcp_tools:
            _mcp_tools_cache = mcp_tools
            app_logger.info(f"成功加载 {len(mcp_tools)} 个 MCP 工具")

        return mcp_tools
    except Exception as e:
        app_logger.error(f"异步加载 MCP 工具失败: {str(e)}")
        import traceback
        app_logger.error(traceback.format_exc())
        return []


def get_available_tools(include_mcp: bool = False) -> List[BaseTool]:
    """
    获取可用的工具列表

    Args:
        include_mcp: 是否包含 MCP 工具（需要先异步加载）
    """
    tools = []

    # RAG知识库工具
    if settings.enable_rag_tool:
        try:
            from .rag_tool import create_rag_search_tool
            rag_tool = create_rag_search_tool()
            tools.append(rag_tool)
            app_logger.info("成功加载 RAG 知识库工具")

            # 添加知识库写入工具
            tools.append(KnowledgeBaseWriteTool())
            tools.append(KnowledgeBaseUpdateTool())
            app_logger.info("成功加载知识库写入和更新工具")
        except Exception as e:
            app_logger.error(f"加载 RAG 工具失败: {str(e)}")

    # MCP工具（从缓存中获取）
    if include_mcp and _mcp_tools_cache:
        tools.extend(_mcp_tools_cache)
        app_logger.info(f"添加 {len(_mcp_tools_cache)} 个 MCP 工具到工具列表")

    return tools


__all__ = [
    "get_available_tools",
    "load_mcp_tools_async",
    "KnowledgeBaseWriteTool",
    "KnowledgeBaseUpdateTool",
]

