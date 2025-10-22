"""
A2A 注册中心 - 自动注册模块
在应用启动时自动创建或更新 AgentCard
"""
from typing import Optional, Dict, Any, List
from src.config import settings
from src.utils import app_logger
from src.utils.a2a_agent_card import AgentCardManager


class A2AAutoRegister:
    """A2A 自动注册管理器"""

    def __init__(self):
        """初始化自动注册管理器"""
        self.manager: Optional[AgentCardManager] = None
        self.registered = False

    async def initialize(self) -> bool:
        """
        初始化 A2A 自动注册

        Returns:
            bool: 初始化是否成功
        """
        try:
            if not settings.a2a_enabled:
                app_logger.info("A2A 未启用，跳过 A2A 自动注册")
                return False

            # 创建 AgentCardManager
            self.manager = AgentCardManager(
                nacos_server=settings.a2a_server_addresses,
                namespace=settings.a2a_namespace,
            )
            app_logger.info("✓ A2A 自动注册管理器初始化成功")
            return True

        except Exception as e:
            app_logger.error(f"✗ A2A 自动注册管理器初始化失败: {str(e)}")
            return False

    async def register_agent_card(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        version: Optional[str] = None,
        url: Optional[str] = None,
        skills: Optional[List[Dict[str, Any]]] = None,
        capabilities: Optional[Dict[str, Any]] = None,
        provider: Optional[Dict[str, str]] = None,
        icon_url: Optional[str] = None,
    ) -> bool:
        """
        注册或更新 AgentCard

        Args:
            name: AgentCard 名称，默认使用 NACOS_SERVICE_NAME
            description: 描述，默认使用 API_TITLE
            version: 版本号，默认使用 API_VERSION
            url: 访问 URL，默认自动生成
            skills: 技能列表
            capabilities: 能力配置
            provider: 提供商信息
            icon_url: 图标 URL

        Returns:
            bool: 注册是否成功
        """
        try:
            if not self.manager:
                app_logger.warning("A2A 管理器未初始化，跳过 AgentCard 注册")
                return False

            # 使用默认值
            agent_name = name or settings.a2a_service_name
            agent_description = description or settings.api_title
            agent_version = version or settings.api_version

            # 自动生成 URL
            if not url:
                # 优先使用 A2A_SERVICE_URL
                if settings.a2a_service_url:
                    url = settings.a2a_service_url
                else:
                    # 使用 A2A 专项配置，如果未设置则回退到通用配置
                    host = settings.a2a_service_host or settings.api_host
                    port = settings.a2a_service_port or settings.api_port

                    # 如果 host 是 0.0.0.0，替换为 127.0.0.1
                    if host == "0.0.0.0":
                        host = "127.0.0.1"

                    url = f"http://{host}:{port}/api/v1/a2a"

            # 默认技能列表
            if not skills:
                skills = [
                    {
                        "id": "rag-search",
                        "name": "RAG 知识库搜索",
                        "description": "在知识库中搜索相关信息",
                        "tags": ["knowledge", "search", "rag"],
                        "inputModes": ["application/json"],
                        "outputModes": ["application/json"],
                    },
                    {
                        "id": "mcp-tools",
                        "name": "MCP 工具调用",
                        "description": "调用 MCP 工具执行任务",
                        "tags": ["tools", "mcp", "execution"],
                        "inputModes": ["application/json"],
                        "outputModes": ["application/json"],
                    },
                    {
                        "id": "agent-chat",
                        "name": "智能体对话",
                        "description": "与智能体进行多轮对话",
                        "tags": ["chat", "conversation", "agent"],
                        "inputModes": ["application/json"],
                        "outputModes": ["application/json"],
                    },
                ]

            # 默认能力配置
            if not capabilities:
                capabilities = {
                    "streaming": True,
                    "pushNotifications": True,
                    "stateTransitionHistory": False,
                }

            # 默认提供商信息
            if not provider:
                provider = {
                    "organization": "Your Organization",
                    "url": "https://ai.com",
                }

            # 创建或更新 AgentCard
            success = self.manager.create_agent_card(
                name=agent_name,
                description=agent_description,
                version=agent_version,
                url=url,
                skills=skills,
                capabilities=capabilities,
                provider=provider,
                icon_url=icon_url,
            )

            if success:
                app_logger.info(f"✓ AgentCard 注册成功: {agent_name} v{agent_version}")
                app_logger.info(f"  - URL: {url}")
                app_logger.info(f"  - 技能数: {len(skills)}")
                self.registered = True
            else:
                app_logger.warning(f"✗ AgentCard 注册失败: {agent_name}")

            return success

        except Exception as e:
            app_logger.error(f"✗ AgentCard 注册异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    async def deregister_agent_card(
        self,
        name: Optional[str] = None,
        version: Optional[str] = None,
    ) -> bool:
        """
        注销 AgentCard

        Args:
            name: AgentCard 名称，默认使用 NACOS_SERVICE_NAME
            version: 版本号，默认使用 API_VERSION

        Returns:
            bool: 注销是否成功
        """
        try:
            if not self.manager:
                app_logger.warning("A2A 管理器未初始化，跳过 AgentCard 注销")
                return False

            agent_name = name or settings.a2a_service_name
            agent_version = version or settings.api_version

            success = self.manager.delete_agent_card(
                agent_name=agent_name,
                version=agent_version,
            )

            if success:
                app_logger.info(f"✓ AgentCard 注销成功: {agent_name} v{agent_version}")
                self.registered = False
            else:
                app_logger.warning(f"✗ AgentCard 注销失败: {agent_name}")

            return success

        except Exception as e:
            app_logger.error(f"✗ AgentCard 注销异常: {str(e)}")
            return False

    async def close(self):
        """关闭自动注册管理器"""
        self.manager = None
        self.registered = False


# 全局单例
_a2a_auto_register: Optional[A2AAutoRegister] = None


def get_a2a_auto_register() -> A2AAutoRegister:
    """获取 A2A 自动注册管理器单例"""
    global _a2a_auto_register
    if _a2a_auto_register is None:
        _a2a_auto_register = A2AAutoRegister()
    return _a2a_auto_register

