"""
A2A Server 辅助模块 - 使用 a2a-sdk 类型定义

使用官方 a2a-sdk 的类型定义确保协议兼容性
实际的 JSON-RPC 处理由 a2a_rpc_routes.py 完成
"""
import uuid
from typing import Any, Dict, List, Optional, AsyncIterator
from a2a.types import (
    Message,
    TextPart,
    Role,
    TaskStatus,
    TaskState,
    Task,
)
from langchain_core.messages import HumanMessage, AIMessage

from src.agent.multi_agent.chat_graph import get_chat_graph
from src.agent.multi_agent.chat_state import create_chat_state
from src.utils import app_logger


class A2AMessageHandler:
    """
    A2A 消息处理器

    使用 a2a-sdk 的类型定义处理消息
    与现有的 LangGraph 智能体系统集成
    """

    def __init__(self):
        """初始化消息处理器"""
        # 任务存储 (简单的内存存储)
        self.tasks: Dict[str, Dict[str, Any]] = {}

        app_logger.info("A2A 消息处理器初始化完成")

    async def handle_message(
        self,
        message: Message,
        metadata: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> AsyncIterator[Message]:
        """
        处理 A2A 消息

        Args:
            message: A2A 消息对象 (使用 a2a-sdk 类型)
            metadata: 元数据
            stream: 是否流式响应

        Yields:
            响应消息 (使用 a2a-sdk 类型)
        """
        try:
            # 提取文本内容
            text_parts = []
            for part in message.parts:
                # a2a-sdk 的 Part 对象可能包装了 TextPart
                if hasattr(part, 'root') and hasattr(part.root, 'text'):
                    text_parts.append(part.root.text)
                elif hasattr(part, 'text'):
                    text_parts.append(part.text)

            if not text_parts:
                error_msg = Message(
                    role=Role.agent,
                    parts=[TextPart(text="错误: 消息中没有文本内容")],
                    message_id=str(uuid.uuid4()),
                    context_id=message.context_id,
                )
                yield error_msg
                return

            question = text_parts[0]
            session_id = message.context_id or str(uuid.uuid4())

            app_logger.info(f"[A2A Handler] 收到消息: {question[:100]}...")
            app_logger.info(f"[A2A Handler] 会话ID: {session_id}")
            app_logger.info(f"[A2A Handler] 流式模式: {stream}")

            # 获取对话图
            chat_graph = get_chat_graph()

            # 创建状态
            state = create_chat_state(
                messages=[HumanMessage(content=question)],
                session_id=session_id
            )

            config = {"configurable": {"thread_id": session_id}}

            if stream:
                # 流式处理
                async for chunk in self._stream_response(chat_graph, state, config, message):
                    yield chunk
            else:
                # 同步处理
                result = await chat_graph.ainvoke(state, config=config)

                # 提取回答
                answer = self._extract_answer(result)

                # 构建响应消息
                response_msg = Message(
                    role=Role.agent,
                    parts=[TextPart(text=answer)],
                    message_id=str(uuid.uuid4()),
                    context_id=session_id,
                )

                app_logger.info(f"[A2A Handler] 响应生成完成: {len(answer)} 字符")
                yield response_msg

        except Exception as e:
            app_logger.error(f"[A2A Handler] 处理消息失败: {e}")
            error_msg = Message(
                role=Role.agent,
                parts=[TextPart(text=f"抱歉，处理您的请求时出现错误: {str(e)}")],
                message_id=str(uuid.uuid4()),
                context_id=message.context_id if message else None,
            )
            yield error_msg

    async def _stream_response(
        self,
        chat_graph,
        state,
        config,
        original_message: Message,
    ) -> AsyncIterator[Message]:
        """
        流式响应处理

        Args:
            chat_graph: 对话图
            state: 初始状态
            config: 配置
            original_message: 原始消息

        Yields:
            流式响应消息
        """
        try:
            accumulated_text = ""

            # 使用 astream_events 获取流式输出
            async for event in chat_graph.astream_events(state, config=config, version="v2"):
                # 只处理 on_chat_model_stream 事件
                if event["event"] == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        content = chunk.content
                        accumulated_text += content

                        # 发送流式消息块
                        chunk_msg = Message(
                            role=Role.agent,
                            parts=[TextPart(text=content)],
                            message_id=str(uuid.uuid4()),
                            context_id=original_message.context_id,
                        )
                        yield chunk_msg

            app_logger.info(f"[A2A Handler] 流式响应完成: {len(accumulated_text)} 字符")

        except Exception as e:
            app_logger.error(f"[A2A Handler] 流式处理失败: {e}")
            error_msg = Message(
                role=Role.agent,
                parts=[TextPart(text=f"流式处理出错: {str(e)}")],
                message_id=str(uuid.uuid4()),
                context_id=original_message.context_id,
            )
            yield error_msg

    def _extract_answer(self, result: Dict[str, Any]) -> str:
        """
        从结果中提取回答

        Args:
            result: 对话图执行结果

        Returns:
            提取的回答文本
        """
        answer = "抱歉，我无法生成响应。"

        messages = result.get("messages") if isinstance(result, dict) else None
        if messages:
            # 从最后一条 AI 消息中提取回答
            for msg in reversed(messages):
                if isinstance(msg, AIMessage):
                    answer = msg.content
                    break

        return answer

    async def get_task(self, task_id: str) -> Optional[Task]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务对象
        """
        task_data = self.tasks.get(task_id)
        if not task_data:
            return None

        return Task(
            id=task_id,
            contextId=task_data.get("context_id", ""),
            status=task_data.get("status"),
        )

    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功取消
        """
        task = self.tasks.get(task_id)
        if not task:
            return False

        # 当前实现不支持真正的任务取消
        # 只是标记状态
        task["status"] = TaskStatus(state=TaskState.canceled)
        return True


# 全局 A2A 消息处理器实例
_a2a_handler: Optional[A2AMessageHandler] = None


def get_a2a_handler() -> A2AMessageHandler:
    """获取全局 A2A 消息处理器实例"""
    global _a2a_handler
    if _a2a_handler is None:
        _a2a_handler = A2AMessageHandler()
    return _a2a_handler

