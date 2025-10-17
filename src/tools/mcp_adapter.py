"""
MCP Tools Adapter - 使用 langchain-mcp-adapters 加载 MCP 工具

这个模块使用官方的 langchain-mcp-adapters 库来加载和管理 MCP 工具。
相比自己实现的 MCP 客户端，这个方案更加成熟和稳定。
"""

import asyncio
from typing import List, Dict, Any
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from src.config.mcp_config import mcp_config_manager
from src.utils import app_logger
from .tool_name_validator import sanitize_tool_names


async def create_mcp_tools_async() -> List[BaseTool]:
    """
    异步加载 MCP 工具

    Returns:
        List[BaseTool]: LangChain 工具列表
    """
    # 检查是否启用
    if not mcp_config_manager.is_enabled():
        app_logger.info("MCP 工具未启用")
        return []

    # 获取启用的服务器
    enabled_servers = mcp_config_manager.get_enabled_servers()
    if not enabled_servers:
        app_logger.warning("没有启用的 MCP 服务器")
        return []

    app_logger.info(f"开始加载 {len(enabled_servers)} 个 MCP 服务器的工具")

    # 构建服务器配置
    server_configs = {}
    for server in enabled_servers:
        # 根据 URL 判断传输类型
        if server.url.startswith("http://") or server.url.startswith("https://"):
            # HTTP 传输
            server_configs[server.name] = {
                "transport": "streamable_http",
                "url": server.url,
            }
        else:
            # stdio 传输 (假设是命令)
            # 这里需要根据实际情况解析命令和参数
            app_logger.warning(f"服务器 {server.name} 使用 stdio 传输，需要配置 command 和 args")
            continue

    if not server_configs:
        app_logger.warning("没有有效的 MCP 服务器配置")
        return []

    try:
        # 创建 MultiServerMCPClient
        client = MultiServerMCPClient(server_configs)

        # 获取所有工具
        tools = await client.get_tools()

        app_logger.info(f"成功加载 {len(tools)} 个 MCP 工具")

        # 清理工具名称，确保符合 OpenAI API 规范
        tools = sanitize_tool_names(tools)

        # 打印工具信息
        for tool in tools:
            app_logger.info(f"  - {tool.name}: {tool.description[:80]}...")

        return tools

    except Exception as e:
        app_logger.error(f"加载 MCP 工具失败: {str(e)}")
        import traceback
        app_logger.error(traceback.format_exc())
        return []


def create_mcp_tools_from_config() -> List[BaseTool]:
    """
    同步方式加载 MCP 工具（用于兼容现有代码）

    Returns:
        List[BaseTool]: LangChain 工具列表
    """
    try:
        # 检查是否已有运行中的事件循环
        try:
            loop = asyncio.get_running_loop()
            # 如果已有事件循环,使用 create_task 或返回空列表
            app_logger.warning("检测到运行中的事件循环,MCP 工具需要在应用启动前加载")
            return []
        except RuntimeError:
            # 没有运行中的事件循环,可以使用 asyncio.run
            return asyncio.run(create_mcp_tools_async())
    except Exception as e:
        app_logger.error(f"同步加载 MCP 工具失败: {str(e)}")
        import traceback
        app_logger.error(traceback.format_exc())
        return []


# 导出函数
__all__ = [
    "create_mcp_tools_async",
    "create_mcp_tools_from_config",
]

