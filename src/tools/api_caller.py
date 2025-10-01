"""
API调用工具
"""
import json
from typing import Optional, Dict, Any
from langchain.tools import BaseTool
from pydantic import Field, ConfigDict
import httpx
from src.utils import app_logger


class APICallTool(BaseTool):
    """API调用工具"""

    name: str = "api_call"
    description: str = """
    调用外部HTTP API。
    输入应该是一个JSON字符串，包含以下字段：
    - url: API地址（必需）
    - method: HTTP方法，如GET、POST等（默认GET）
    - headers: 请求头（可选）
    - params: URL参数（可选）
    - data: 请求体数据（可选）

    示例输入：
    {
        "url": "https://api.example.com/data",
        "method": "GET",
        "params": {"key": "value"}
    }
    """

    timeout: int = Field(default=30)

    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def _run(self, query: str) -> str:
        """执行API调用"""
        try:
            # 解析输入
            params = json.loads(query)
            url = params.get("url")
            method = params.get("method", "GET").upper()
            headers = params.get("headers", {})
            url_params = params.get("params", {})
            data = params.get("data")
            
            if not url:
                return "错误：缺少url参数"
            
            app_logger.info(f"调用API: {method} {url}")
            
            # 发送HTTP请求
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=url_params,
                    json=data if data else None
                )
                
                response.raise_for_status()
                
                # 尝试解析JSON响应
                try:
                    result = response.json()
                    return json.dumps(result, ensure_ascii=False, indent=2)
                except:
                    return response.text
                    
        except json.JSONDecodeError as e:
            app_logger.error(f"JSON解析失败: {str(e)}")
            return f"输入格式错误，请提供有效的JSON字符串: {str(e)}"
        except httpx.HTTPError as e:
            app_logger.error(f"API调用失败: {str(e)}")
            return f"API调用失败: {str(e)}"
        except Exception as e:
            app_logger.error(f"API调用异常: {str(e)}")
            return f"API调用异常: {str(e)}"
    
    async def _arun(self, query: str) -> str:
        """异步执行API调用"""
        try:
            # 解析输入
            params = json.loads(query)
            url = params.get("url")
            method = params.get("method", "GET").upper()
            headers = params.get("headers", {})
            url_params = params.get("params", {})
            data = params.get("data")
            
            if not url:
                return "错误：缺少url参数"
            
            app_logger.info(f"异步调用API: {method} {url}")
            
            # 发送异步HTTP请求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=url_params,
                    json=data if data else None
                )
                
                response.raise_for_status()
                
                # 尝试解析JSON响应
                try:
                    result = response.json()
                    return json.dumps(result, ensure_ascii=False, indent=2)
                except:
                    return response.text
                    
        except json.JSONDecodeError as e:
            app_logger.error(f"JSON解析失败: {str(e)}")
            return f"输入格式错误，请提供有效的JSON字符串: {str(e)}"
        except httpx.HTTPError as e:
            app_logger.error(f"API调用失败: {str(e)}")
            return f"API调用失败: {str(e)}"
        except Exception as e:
            app_logger.error(f"API调用异常: {str(e)}")
            return f"API调用异常: {str(e)}"

