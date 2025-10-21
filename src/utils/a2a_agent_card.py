"""
A2A 注册中心 - AgentCard 管理
实现 Nacos A2A 注册中心的 AgentCard 管理功能
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import requests

from src.config import settings
from src.utils import app_logger


class AgentCardManager:
    """AgentCard 管理器"""

    def __init__(self, nacos_server: str, namespace: str = "public"):
        """
        初始化 AgentCard 管理器

        Args:
            nacos_server: Nacos 服务器地址（格式：host:port）
            namespace: 命名空间，默认为 public
        """
        self.nacos_server = nacos_server
        self.namespace = namespace
        self.base_url = f"http://{nacos_server}/nacos/v3/admin/ai/a2a"
        self.auth_url = f"http://{nacos_server}/nacos/v1/auth/login"
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None

        # 如果配置了用户名和密码，获取访问令牌
        if settings.a2a_username and settings.a2a_password:
            self._get_access_token()

    def _get_access_token(self) -> bool:
        """
        获取 Nacos 访问令牌

        Returns:
            bool: 是否成功获取令牌
        """
        try:
            response = requests.post(
                self.auth_url,
                data={
                    "username": settings.a2a_username,
                    "password": settings.a2a_password,
                },
                timeout=10,
            )

            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get("accessToken")
                token_ttl = result.get("tokenTtl", 18000)  # 默认 5 小时
                self.token_expiry = datetime.now().timestamp() + token_ttl
                app_logger.info("✓ Nacos 访问令牌获取成功")
                return True
            else:
                app_logger.error(f"✗ 获取访问令牌失败: HTTP {response.status_code}")
                return False

        except Exception as e:
            app_logger.error(f"✗ 获取访问令牌异常: {str(e)}")
            return False

    def _ensure_token_valid(self) -> bool:
        """
        确保访问令牌有效，如果过期则重新获取

        Returns:
            bool: 令牌是否有效
        """
        if not self.access_token:
            return self._get_access_token()

        # 检查令牌是否即将过期（提前 5 分钟刷新）
        if self.token_expiry and datetime.now().timestamp() > (self.token_expiry - 300):
            app_logger.info("访问令牌即将过期，重新获取...")
            return self._get_access_token()

        return True

    def _get_headers(self, content_type: str = "application/json") -> Dict[str, str]:
        """
        获取请求头，包含访问令牌

        Args:
            content_type: Content-Type 类型

        Returns:
            Dict: 请求头
        """
        headers = {"Content-Type": content_type}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def create_agent_card(
        self,
        name: str,
        description: str,
        version: str = "1.0.0",
        url: Optional[str] = None,
        protocol_version: str = "0.2.9",
        preferred_transport: str = "JSONRPC",
        registration_type: str = "SERVICE",
        capabilities: Optional[Dict[str, Any]] = None,
        skills: Optional[List[Dict[str, Any]]] = None,
        provider: Optional[Dict[str, str]] = None,
        icon_url: Optional[str] = None,
    ) -> bool:
        """
        创建 AgentCard

        Args:
            name: AgentCard 名称
            description: 描述
            version: 版本号
            url: 访问 URL
            protocol_version: A2A 协议版本
            preferred_transport: 首选传输协议
            registration_type: 注册类型（URL 或 SERVICE）
            capabilities: 能力配置
            skills: 技能列表
            provider: 提供商信息
            icon_url: 图标 URL

        Returns:
            bool: 创建是否成功
        """
        try:
            # 确保令牌有效
            if not self._ensure_token_valid():
                app_logger.error("✗ 无法获取有效的访问令牌")
                return False

            # 构建 AgentCard 对象
            agent_card = {
                "protocolVersion": protocol_version,
                "name": name,
                "description": description,
                "version": version,
                "preferredTransport": preferred_transport,
                "capabilities": capabilities or {
                    "streaming": True,
                    "pushNotifications": True,
                    "stateTransitionHistory": False,
                },
                "skills": skills or [],
                "defaultInputModes": ["application/json", "text/plain"],
                "defaultOutputModes": ["application/json"],
            }

            # 添加可选字段
            if url:
                agent_card["url"] = url
            if icon_url:
                agent_card["iconUrl"] = icon_url
            if provider:
                agent_card["provider"] = provider

            # 发送请求
            params = {
                "namespaceId": self.namespace,
                "registrationType": registration_type,
            }
            data = {
                "agentCard": json.dumps(agent_card),
            }

            response = requests.post(
                self.base_url,
                params=params,
                data=data,
                headers=self._get_headers(content_type="application/x-www-form-urlencoded"),
                timeout=10,
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    app_logger.info(f"✓ AgentCard 创建成功: {name} v{version}")
                    return True
                else:
                    app_logger.error(f"✗ AgentCard 创建失败: {result.get('message')}")
                    return False
            else:
                app_logger.error(f"✗ 请求失败: HTTP {response.status_code}")
                app_logger.error(f"  响应内容: {response.text}")
                return False

        except Exception as e:
            app_logger.error(f"✗ 创建 AgentCard 失败: {str(e)}")
            return False

    def get_agent_card(
        self,
        agent_name: str,
        version: Optional[str] = None,
        registration_type: str = "SERVICE",
    ) -> Optional[Dict[str, Any]]:
        """
        获取 AgentCard 详情

        Args:
            agent_name: AgentCard 名称
            version: 版本号（可选，默认为最新版本）
            registration_type: 注册类型

        Returns:
            Dict: AgentCard 详情，失败返回 None
        """
        try:
            # 确保令牌有效
            if not self._ensure_token_valid():
                app_logger.error("✗ 无法获取有效的访问令牌")
                return None

            params = {
                "namespaceId": self.namespace,
                "agentName": agent_name,
                "registrationType": registration_type,
            }
            if version:
                params["version"] = version

            response = requests.get(
                self.base_url,
                params=params,
                headers=self._get_headers(),
                timeout=10,
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    app_logger.info(f"✓ 获取 AgentCard 成功: {agent_name}")
                    return result.get("data")
                else:
                    app_logger.error(f"✗ 获取 AgentCard 失败: {result.get('message')}")
                    return None
            else:
                app_logger.error(f"✗ 请求失败: HTTP {response.status_code}")
                return None

        except Exception as e:
            app_logger.error(f"✗ 获取 AgentCard 失败: {str(e)}")
            return None

    def list_agent_cards(
        self,
        page_no: int = 1,
        page_size: int = 100,
        agent_name: Optional[str] = None,
        search: str = "blur",
    ) -> Optional[Dict[str, Any]]:
        """
        列出 AgentCard

        Args:
            page_no: 页码
            page_size: 每页条数
            agent_name: AgentCard 名称（可选）
            search: 搜索类型（blur 或 accurate）

        Returns:
            Dict: AgentCard 列表，失败返回 None
        """
        try:
            # 确保令牌有效
            if not self._ensure_token_valid():
                app_logger.error("✗ 无法获取有效的访问令牌")
                return None

            params = {
                "namespaceId": self.namespace,
                "pageNo": page_no,
                "pageSize": page_size,
                "search": search,
            }
            if agent_name:
                params["agentName"] = agent_name

            response = requests.get(
                f"{self.base_url}/list",
                params=params,
                headers=self._get_headers(),
                timeout=10,
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    app_logger.info(f"✓ 获取 AgentCard 列表成功")
                    return result.get("data")
                else:
                    app_logger.error(f"✗ 获取列表失败: {result.get('message')}")
                    return None
            else:
                app_logger.error(f"✗ 请求失败: HTTP {response.status_code}")
                return None

        except Exception as e:
            app_logger.error(f"✗ 获取 AgentCard 列表失败: {str(e)}")
            return None

    def delete_agent_card(
        self,
        agent_name: str,
        version: Optional[str] = None,
    ) -> bool:
        """
        删除 AgentCard

        Args:
            agent_name: AgentCard 名称
            version: 版本号（可选，默认为最新版本）

        Returns:
            bool: 删除是否成功
        """
        try:
            # 确保令牌有效
            if not self._ensure_token_valid():
                app_logger.error("✗ 无法获取有效的访问令牌")
                return False

            params = {
                "namespaceId": self.namespace,
                "agentName": agent_name,
            }
            if version:
                params["version"] = version

            response = requests.delete(
                self.base_url,
                params=params,
                headers=self._get_headers(),
                timeout=10,
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    app_logger.info(f"✓ AgentCard 删除成功: {agent_name}")
                    return True
                else:
                    app_logger.error(f"✗ AgentCard 删除失败: {result.get('message')}")
                    return False
            else:
                app_logger.error(f"✗ 请求失败: HTTP {response.status_code}")
                return False

        except Exception as e:
            app_logger.error(f"✗ 删除 AgentCard 失败: {str(e)}")
            return False

    def get_version_list(self, agent_name: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取 AgentCard 版本列表

        Args:
            agent_name: AgentCard 名称

        Returns:
            List: 版本列表，失败返回 None
        """
        try:
            # 确保令牌有效
            if not self._ensure_token_valid():
                app_logger.error("✗ 无法获取有效的访问令牌")
                return None

            params = {
                "namespaceId": self.namespace,
                "agentName": agent_name,
            }

            response = requests.get(
                f"{self.base_url}/version/list",
                params=params,
                headers=self._get_headers(),
                timeout=10,
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    app_logger.info(f"✓ 获取版本列表成功: {agent_name}")
                    return result.get("data", [])
                else:
                    app_logger.error(f"✗ 获取版本列表失败: {result.get('message')}")
                    return None
            else:
                app_logger.error(f"✗ 请求失败: HTTP {response.status_code}")
                return None

        except Exception as e:
            app_logger.error(f"✗ 获取版本列表失败: {str(e)}")
            return None

