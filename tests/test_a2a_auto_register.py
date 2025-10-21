"""
A2A 自动注册模块测试
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.utils.a2a_auto_register import A2AAutoRegister, get_a2a_auto_register
from src.config import settings


class TestA2AAutoRegister:
    """A2A 自动注册测试"""

    @pytest.mark.asyncio
    async def test_initialize_a2a_disabled(self):
        """测试 A2A 禁用时的初始化"""
        with patch('src.utils.a2a_auto_register.settings.a2a_enabled', False):
            register = A2AAutoRegister()
            result = await register.initialize()
            assert result is False
            assert register.manager is None

    @pytest.mark.asyncio
    async def test_initialize_a2a_enabled(self):
        """测试 A2A 启用时的初始化"""
        with patch('src.utils.a2a_auto_register.settings.a2a_enabled', True):
            with patch('src.utils.a2a_auto_register.settings.a2a_server_addresses', '127.0.0.1:8848'):
                with patch('src.utils.a2a_auto_register.settings.a2a_namespace', 'public'):
                    register = A2AAutoRegister()
                    result = await register.initialize()
                    assert result is True
                    assert register.manager is not None

    @pytest.mark.asyncio
    async def test_register_agent_card_no_manager(self):
        """测试没有管理器时的注册"""
        register = A2AAutoRegister()
        result = await register.register_agent_card()
        assert result is False
        assert register.registered is False

    @pytest.mark.asyncio
    async def test_register_agent_card_with_defaults(self):
        """测试使用默认值的注册"""
        register = A2AAutoRegister()

        # 创建 mock 管理器
        mock_manager = Mock()
        mock_manager.create_agent_card = Mock(return_value=True)
        register.manager = mock_manager

        # 执行注册
        result = await register.register_agent_card()

        # 验证结果
        assert result is True
        assert register.registered is True
        mock_manager.create_agent_card.assert_called_once()

        # 验证调用参数
        call_args = mock_manager.create_agent_card.call_args
        assert call_args[1]['name'] == settings.a2a_service_name
        assert call_args[1]['description'] == settings.api_title
        assert call_args[1]['version'] == settings.api_version
        assert 'skills' in call_args[1]
        assert len(call_args[1]['skills']) == 3

    @pytest.mark.asyncio
    async def test_register_agent_card_with_custom_values(self):
        """测试使用自定义值的注册"""
        register = A2AAutoRegister()

        # 创建 mock 管理器
        mock_manager = Mock()
        mock_manager.create_agent_card = Mock(return_value=True)
        register.manager = mock_manager

        # 自定义参数
        custom_skills = [
            {
                "id": "custom-skill",
                "name": "Custom Skill",
                "description": "A custom skill",
                "tags": ["custom"],
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
            }
        ]

        # 执行注册
        result = await register.register_agent_card(
            name="custom-agent",
            description="Custom Agent",
            version="2.0.0",
            url="http://custom:8000/a2a/v1",
            skills=custom_skills,
        )

        # 验证结果
        assert result is True
        assert register.registered is True

        # 验证调用参数
        call_args = mock_manager.create_agent_card.call_args
        assert call_args[1]['name'] == "custom-agent"
        assert call_args[1]['description'] == "Custom Agent"
        assert call_args[1]['version'] == "2.0.0"
        assert call_args[1]['url'] == "http://custom:8000/a2a/v1"
        assert call_args[1]['skills'] == custom_skills

    @pytest.mark.asyncio
    async def test_register_agent_card_failure(self):
        """测试注册失败的情况"""
        register = A2AAutoRegister()

        # 创建 mock 管理器
        mock_manager = Mock()
        mock_manager.create_agent_card = Mock(return_value=False)
        register.manager = mock_manager

        # 执行注册
        result = await register.register_agent_card()

        # 验证结果
        assert result is False
        assert register.registered is False

    @pytest.mark.asyncio
    async def test_register_agent_card_exception(self):
        """测试注册异常的情况"""
        register = A2AAutoRegister()

        # 创建 mock 管理器
        mock_manager = Mock()
        mock_manager.create_agent_card = Mock(side_effect=Exception("Test error"))
        register.manager = mock_manager

        # 执行注册
        result = await register.register_agent_card()

        # 验证结果
        assert result is False
        assert register.registered is False

    @pytest.mark.asyncio
    async def test_deregister_agent_card_no_manager(self):
        """测试没有管理器时的注销"""
        register = A2AAutoRegister()
        result = await register.deregister_agent_card()
        assert result is False

    @pytest.mark.asyncio
    async def test_deregister_agent_card_success(self):
        """测试成功注销"""
        register = A2AAutoRegister()
        register.registered = True

        # 创建 mock 管理器
        mock_manager = Mock()
        mock_manager.delete_agent_card = Mock(return_value=True)
        register.manager = mock_manager

        # 执行注销
        result = await register.deregister_agent_card()

        # 验证结果
        assert result is True
        assert register.registered is False
        mock_manager.delete_agent_card.assert_called_once()

    @pytest.mark.asyncio
    async def test_deregister_agent_card_failure(self):
        """测试注销失败"""
        register = A2AAutoRegister()
        register.registered = True

        # 创建 mock 管理器
        mock_manager = Mock()
        mock_manager.delete_agent_card = Mock(return_value=False)
        register.manager = mock_manager

        # 执行注销
        result = await register.deregister_agent_card()

        # 验证结果
        assert result is False
        assert register.registered is True

    @pytest.mark.asyncio
    async def test_close(self):
        """测试关闭"""
        register = A2AAutoRegister()
        register.registered = True
        register.manager = Mock()

        # 执行关闭
        await register.close()

        # 验证结果
        assert register.manager is None
        assert register.registered is False

    def test_get_a2a_auto_register_singleton(self):
        """测试单例获取"""
        register1 = get_a2a_auto_register()
        register2 = get_a2a_auto_register()
        assert register1 is register2

