"""
测试 A2A SDK 集成

测试基于 a2a-sdk 类型定义的 A2A 消息处理器
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.agent.a2a_server import A2AMessageHandler, get_a2a_handler
from a2a.types import Message, TextPart, Role, TaskStatus, TaskState


class TestA2AMessageHandler:
    """测试 A2A 消息处理器"""

    @pytest.fixture
    def a2a_handler(self):
        """创建 A2A 消息处理器实例"""
        return A2AMessageHandler()

    def test_handler_initialization(self, a2a_handler):
        """测试处理器初始化"""
        assert isinstance(a2a_handler.tasks, dict)

    def test_get_a2a_handler_singleton(self):
        """测试全局单例"""
        handler1 = get_a2a_handler()
        handler2 = get_a2a_handler()
        assert handler1 is handler2

    @pytest.mark.asyncio
    async def test_handle_message_no_text(self, a2a_handler):
        """测试处理没有文本内容的消息"""
        message = Message(
            role=Role.user,
            parts=[],
            message_id="test-msg-1",
            context_id="test-ctx-1",
        )

        responses = []
        async for response in a2a_handler.handle_message(message, stream=False):
            responses.append(response)

        assert len(responses) == 1
        # Part 对象包装了 TextPart,需要访问 root 属性
        first_part = responses[0].parts[0]
        if hasattr(first_part, 'root'):
            assert "错误" in first_part.root.text
        else:
            assert "错误" in first_part.text

    @pytest.mark.asyncio
    async def test_handle_message_sync(self, a2a_handler):
        """测试同步消息处理"""
        # Mock chat_graph
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            "messages": [
                MagicMock(content="这是一个测试回答", __class__=MagicMock(__name__="AIMessage"))
            ]
        })

        with patch("src.agent.a2a_server.get_chat_graph", return_value=mock_graph):
            message = Message(
                role=Role.user,
                parts=[TextPart(text="你好")],
                message_id="test-msg-2",
                context_id="test-ctx-2",
            )

            responses = []
            async for response in a2a_handler.handle_message(message, stream=False):
                responses.append(response)

            assert len(responses) == 1
            assert responses[0].role == Role.agent
            assert len(responses[0].parts) > 0
            assert responses[0].context_id == "test-ctx-2"

    @pytest.mark.asyncio
    async def test_handle_message_error(self, a2a_handler):
        """测试消息处理错误"""
        # Mock chat_graph to raise exception
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(side_effect=Exception("测试错误"))

        with patch("src.agent.a2a_server.get_chat_graph", return_value=mock_graph):
            message = Message(
                role=Role.user,
                parts=[TextPart(text="测试错误")],
                message_id="test-msg-3",
                context_id="test-ctx-3",
            )

            responses = []
            async for response in a2a_handler.handle_message(message, stream=False):
                responses.append(response)

            assert len(responses) == 1
            # Part 对象包装了 TextPart,需要访问 root 属性
            first_part = responses[0].parts[0]
            if hasattr(first_part, 'root'):
                assert "错误" in first_part.root.text
            else:
                assert "错误" in first_part.text

    def test_extract_answer_with_ai_message(self, a2a_handler):
        """测试从结果中提取 AI 消息"""
        from langchain_core.messages import AIMessage, HumanMessage

        result = {
            "messages": [
                HumanMessage(content="问题"),
                AIMessage(content="这是回答"),
            ]
        }

        answer = a2a_handler._extract_answer(result)
        assert answer == "这是回答"

    def test_extract_answer_no_ai_message(self, a2a_handler):
        """测试没有 AI 消息的情况"""
        from langchain_core.messages import HumanMessage

        result = {
            "messages": [
                HumanMessage(content="问题"),
            ]
        }

        answer = a2a_handler._extract_answer(result)
        assert "抱歉" in answer

    def test_extract_answer_empty_result(self, a2a_handler):
        """测试空结果"""
        result = {}
        answer = a2a_handler._extract_answer(result)
        assert "抱歉" in answer

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, a2a_handler):
        """测试获取不存在的任务"""
        result = await a2a_handler.get_task("non-existent-task")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_task_exists(self, a2a_handler):
        """测试获取存在的任务"""
        # 添加一个任务
        task_status = TaskStatus(state=TaskState.completed)
        a2a_handler.tasks["test-task-1"] = {
            "status": task_status,
            "context_id": "test-ctx-1",
        }

        result = await a2a_handler.get_task("test-task-1")
        assert result is not None
        assert result.id == "test-task-1"
        assert result.status.state == TaskState.completed

    @pytest.mark.asyncio
    async def test_cancel_task_not_found(self, a2a_handler):
        """测试取消不存在的任务"""
        success = await a2a_handler.cancel_task("non-existent-task")
        assert success is False

    @pytest.mark.asyncio
    async def test_cancel_task_exists(self, a2a_handler):
        """测试取消存在的任务"""
        # 添加一个任务
        task_status = TaskStatus(state=TaskState.working)
        a2a_handler.tasks["test-task-2"] = {
            "status": task_status,
        }

        success = await a2a_handler.cancel_task("test-task-2")
        assert success is True
        assert a2a_handler.tasks["test-task-2"]["status"].state == TaskState.canceled


class TestA2ASDKRoutes:
    """测试 A2A SDK 路由"""

    @pytest.mark.asyncio
    async def test_a2a_sdk_health(self):
        """测试健康检查端点"""
        from src.api.a2a_sdk_routes import a2a_sdk_health

        response = await a2a_sdk_health()
        assert response["status"] == "healthy"
        assert response["service"] == "a2a-sdk"
        assert "version" in response

    @pytest.mark.asyncio
    async def test_a2a_sdk_info(self):
        """测试信息端点"""
        from src.api.a2a_sdk_routes import a2a_sdk_info

        response = await a2a_sdk_info()
        assert response["name"] == "cus-ai-agent"
        assert response["version"] == "1.0.0"
        assert "features" in response
        assert "endpoints" in response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

