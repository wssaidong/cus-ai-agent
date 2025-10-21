"""
MCP Tools Adapter - 使用 langchain-mcp-adapters 加载 MCP 工具

这个模块使用官方的 langchain-mcp-adapters 库来加载和管理 MCP 工具。
相比自己实现的 MCP 客户端，这个方案更加成熟和稳定。
"""

import asyncio
from typing import List, Dict, Any
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from src.config.mcp_config import mcp_config_manager, MCPServerConfig
from src.utils import app_logger
from .tool_name_validator import sanitize_tool_names


def _filter_tools_by_config(tools: List[BaseTool], enabled_servers: List[MCPServerConfig]) -> List[BaseTool]:
    """
    根据配置过滤工具

    Args:
        tools: 所有加载的工具列表
        enabled_servers: 启用的服务器配置列表

    Returns:
        过滤后的工具列表
    """
    if not tools or not enabled_servers:
        return tools

    # 构建服务器名称到配置的映射
    server_config_map = {server.name: server for server in enabled_servers}

    filtered_tools = []
    excluded_count = 0

    # 调试：打印工具对象的属性
    if tools:
        app_logger.debug(f"工具对象类型: {type(tools[0])}")
        app_logger.debug(f"工具对象属性: {dir(tools[0])}")
        if hasattr(tools[0], '__dict__'):
            app_logger.debug(f"工具对象 __dict__: {tools[0].__dict__}")

    for tool in tools:
        # 尝试从工具对象中提取服务器名称
        # langchain-mcp-adapters 可能在工具的 metadata 或其他属性中存储服务器信息

        server_name = None

        # 方式1：检查 server_name 属性
        if hasattr(tool, 'server_name'):
            server_name = tool.server_name

        # 方式2：检查 metadata 中的 server_name
        elif hasattr(tool, 'metadata') and isinstance(tool.metadata, dict):
            server_name = tool.metadata.get('server_name')

        # 方式3：检查 extra 属性
        elif hasattr(tool, 'extra') and isinstance(tool.extra, dict):
            server_name = tool.extra.get('server_name')

        # 方式4：从工具的 func 属性中查找
        elif hasattr(tool, 'func') and hasattr(tool.func, '__self__'):
            # 检查是否是绑定方法，可能包含服务器信息
            obj = tool.func.__self__
            if hasattr(obj, 'server_name'):
                server_name = obj.server_name

        if not server_name:
            # 如果无法确定服务器名称，假设来自唯一的启用服务器
            if len(enabled_servers) == 1:
                server_name = enabled_servers[0].name
                app_logger.debug(f"工具 {tool.name} 无法确定服务器，假设来自 {server_name}")
            else:
                # 多个服务器时无法确定，包含工具
                app_logger.debug(f"工具 {tool.name} 无法确定服务器，包含此工具")
                filtered_tools.append(tool)
                continue

        # 获取服务器配置
        server_config = server_config_map.get(server_name)
        if not server_config:
            # 服务器配置不存在，包含工具
            app_logger.debug(f"服务器 {server_name} 配置不存在，包含工具 {tool.name}")
            filtered_tools.append(tool)
            continue

        # 检查工具是否应该被包含
        if mcp_config_manager.should_include_tool(server_name, tool.name):
            filtered_tools.append(tool)
        else:
            excluded_count += 1
            app_logger.info(f"过滤掉工具: {tool.name} (来自服务器: {server_name})")

    if excluded_count > 0:
        app_logger.info(f"工具过滤完成: 排除了 {excluded_count} 个工具，保留了 {len(filtered_tools)} 个工具")

    return filtered_tools


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

        # 应用工具过滤
        tools = _filter_tools_by_config(tools, enabled_servers)

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

