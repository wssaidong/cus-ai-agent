"""
MCP (Model Context Protocol) 客户端
用于连接和调用外部 MCP 服务器的工具
"""
import json
import httpx
from typing import Dict, List, Any, Optional
from langchain.tools import BaseTool
from pydantic import Field, ConfigDict
from src.utils import app_logger


class MCPClient:
    """MCP 客户端,用于与 MCP 服务器通信"""
    
    def __init__(self, server_url: str, timeout: int = 30):
        """
        初始化 MCP 客户端
        
        Args:
            server_url: MCP 服务器地址
            timeout: 请求超时时间(秒)
        """
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
        self._tools_cache: Optional[List[Dict[str, Any]]] = None
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        获取 MCP 服务器提供的工具列表

        Returns:
            工具列表
        """
        try:
            # 使用较短的超时时间，避免启动卡住
            timeout_config = httpx.Timeout(
                connect=3.0,  # 连接超时 3 秒
                read=self.timeout,  # 读取超时使用配置的值
                write=5.0,  # 写入超时 5 秒
                pool=5.0  # 连接池超时 5 秒
            )

            async with httpx.AsyncClient(timeout=timeout_config) as client:
                response = await client.post(
                    self.server_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/list",
                        "params": {}
                    }
                )
                response.raise_for_status()
                result = response.json()

                if "error" in result:
                    raise Exception(f"MCP错误: {result['error']}")
                
                tools = result.get("result", {}).get("tools", [])
                self._tools_cache = tools
                return tools
                
        except Exception as e:
            app_logger.error(f"获取MCP工具列表失败: {str(e)}")
            return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用 MCP 工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.server_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": tool_name,
                            "arguments": arguments
                        }
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                if "error" in result:
                    return {
                        "success": False,
                        "error": result["error"]["message"]
                    }
                
                tool_result = result.get("result", {})
                is_error = tool_result.get("isError", False)
                content = tool_result.get("content", [])
                
                # 提取文本内容
                text_content = []
                for item in content:
                    if item.get("type") == "text":
                        text_content.append(item.get("text", ""))
                
                return {
                    "success": not is_error,
                    "content": "\n".join(text_content),
                    "raw_result": tool_result
                }
                
        except Exception as e:
            app_logger.error(f"调用MCP工具失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


class MCPToolWrapper(BaseTool):
    """
    MCP 工具包装器,将 MCP 工具转换为 LangChain 工具
    """

    name: str
    description: str
    mcp_client: Any = Field(exclude=True)
    tool_name: str
    mcp_input_schema: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def _run(self, query: str) -> str:
        """
        同步执行工具(通过异步实现)
        
        Args:
            query: 工具输入,应该是JSON格式的参数
            
        Returns:
            工具执行结果
        """
        import asyncio
        
        try:
            # 解析输入参数
            if isinstance(query, str):
                try:
                    arguments = json.loads(query)
                except json.JSONDecodeError:
                    # 如果不是JSON,尝试作为单个参数
                    # 从 mcp_input_schema 获取第一个必需参数
                    properties = self.mcp_input_schema.get("properties", {})
                    required = self.mcp_input_schema.get("required", [])
                    if required and len(required) > 0:
                        first_param = required[0]
                        arguments = {first_param: query}
                    else:
                        arguments = {"input": query}
            else:
                arguments = query
            
            # 调用异步方法
            try:
                loop = asyncio.get_running_loop()
                # 如果有运行中的循环，在新线程中运行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.mcp_client.call_tool(self.tool_name, arguments)
                    )
                    result = future.result(timeout=self.mcp_client.timeout)
            except RuntimeError:
                # 没有运行中的循环，直接运行
                result = asyncio.run(self.mcp_client.call_tool(self.tool_name, arguments))

            if result.get("success"):
                return result.get("content", "")
            else:
                return f"错误: {result.get('error', '未知错误')}"

        except Exception as e:
            app_logger.error(f"执行MCP工具失败: {str(e)}")
            return f"执行失败: {str(e)}"
    
    async def _arun(self, query: str) -> str:
        """
        异步执行工具
        
        Args:
            query: 工具输入
            
        Returns:
            工具执行结果
        """
        try:
            # 解析输入参数
            if isinstance(query, str):
                try:
                    arguments = json.loads(query)
                except json.JSONDecodeError:
                    properties = self.mcp_input_schema.get("properties", {})
                    required = self.mcp_input_schema.get("required", [])
                    if required and len(required) > 0:
                        first_param = required[0]
                        arguments = {first_param: query}
                    else:
                        arguments = {"input": query}
            else:
                arguments = query
            
            result = await self.mcp_client.call_tool(self.tool_name, arguments)
            
            if result.get("success"):
                return result.get("content", "")
            else:
                return f"错误: {result.get('error', '未知错误')}"
                
        except Exception as e:
            app_logger.error(f"执行MCP工具失败: {str(e)}")
            return f"执行失败: {str(e)}"


async def create_mcp_tools(server_url: str, timeout: int = 30) -> List[BaseTool]:
    """
    从 MCP 服务器创建工具列表
    
    Args:
        server_url: MCP 服务器地址
        timeout: 请求超时时间
        
    Returns:
        LangChain 工具列表
    """
    client = MCPClient(server_url, timeout)
    tools_list = await client.list_tools()
    
    langchain_tools = []
    for tool_def in tools_list:
        try:
            tool = MCPToolWrapper(
                name=tool_def.get("name", "unknown"),
                description=tool_def.get("description", "MCP工具"),
                mcp_client=client,
                tool_name=tool_def.get("name", "unknown"),
                mcp_input_schema=tool_def.get("inputSchema", {})
            )
            langchain_tools.append(tool)
            app_logger.info(f"加载MCP工具: {tool.name}")
        except Exception as e:
            app_logger.error(f"创建MCP工具失败: {str(e)}")
    
    return langchain_tools


def create_mcp_tools_sync(server_url: str, timeout: int = 30) -> List[BaseTool]:
    """
    同步版本的创建 MCP 工具

    Args:
        server_url: MCP 服务器地址
        timeout: 请求超时时间

    Returns:
        LangChain 工具列表
    """
    import asyncio

    try:
        # 尝试获取当前事件循环
        try:
            loop = asyncio.get_running_loop()
            # 如果有运行中的循环，创建新的线程来运行异步代码
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, create_mcp_tools(server_url, timeout))
                return future.result(timeout=timeout + 5)
        except RuntimeError:
            # 没有运行中的循环，直接使用 asyncio.run
            return asyncio.run(create_mcp_tools(server_url, timeout))
    except Exception as e:
        app_logger.error(f"创建MCP工具失败: {str(e)}")
        return []

