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


async def create_mcp_tools_async() -> List[BaseTool]:
    """
    异步加载 MCP 工具

    改进方案：分别加载每个服务器的工具，在加载时就应用过滤配置
    这样可以确保多服务器场景下 include/exclude 配置正常工作

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

        # 分别加载每个服务器的工具，并应用过滤
        all_tools = []
        total_excluded = 0

        for server in enabled_servers:
            if server.name not in server_configs:
                continue

            try:
                # 使用 server_name 参数只加载指定服务器的工具
                server_tools = await client.get_tools(server_name=server.name)

                app_logger.info(f"从服务器 {server.name} 加载了 {len(server_tools)} 个工具")

                # 应用工具过滤配置
                if server.tools:
                    filtered_tools = []
                    for tool in server_tools:
                        if mcp_config_manager.should_include_tool(server.name, tool.name):
                            filtered_tools.append(tool)
                        else:
                            total_excluded += 1
                            app_logger.info(f"过滤掉工具: {tool.name} (来自服务器: {server.name})")

                    app_logger.info(f"服务器 {server.name}: 保留 {len(filtered_tools)}/{len(server_tools)} 个工具")
                    all_tools.extend(filtered_tools)
                else:
                    # 没有配置过滤，包含所有工具
                    all_tools.extend(server_tools)

            except Exception as e:
                app_logger.error(f"加载服务器 {server.name} 的工具失败: {str(e)}")
                continue

        if total_excluded > 0:
            app_logger.info(f"工具过滤完成: 总共排除了 {total_excluded} 个工具，保留了 {len(all_tools)} 个工具")
        else:
            app_logger.info(f"成功加载 {len(all_tools)} 个 MCP 工具")

        # 清理工具名称，确保符合 OpenAI API 规范
        all_tools = sanitize_tool_names(all_tools)

        # 打印工具信息
        for tool in all_tools:
            app_logger.info(f"  - {tool.name}: {tool.description[:80]}...")

        return all_tools

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

