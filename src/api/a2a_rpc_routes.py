"""A2A JSON-RPC 路由

使用 a2a-sdk 官方服务器实现，不自己实现 JSON-RPC 协议。
提供 RequestHandler 实现来处理 A2A 协议请求。
"""
import uuid
from typing import AsyncGenerator, Optional

from a2a.server.request_handlers.request_handler import RequestHandler
from a2a.server.context import ServerCallContext
from a2a.server.events.event_queue import Event
from a2a.types import (
    Message,
    Task,
    TaskStatus,
    TaskState,
    TextPart,
    Role,
    MessageSendParams,
    TaskQueryParams,
    TaskIdParams,
    TaskPushNotificationConfig,
    TaskStatusUpdateEvent,
)

from langchain_core.messages import HumanMessage

from src.agent.multi_agent.chat_graph import get_chat_graph
from src.agent.multi_agent.chat_state import create_chat_state
from src.api.openai_routes import stream_graph
from src.utils import app_logger


class A2ARequestHandler(RequestHandler):
    """A2A 请求处理器实现

    实现 a2a-sdk 的 RequestHandler 接口，处理所有 A2A 协议请求。
    """

    def __init__(self):
        """初始化请求处理器"""
        self.tasks = {}  # 简单的内存任务存储
        app_logger.info("[A2A Handler] 初始化 A2A 请求处理器")


    async def on_message_send(
        self,
        params: MessageSendParams,
        context: Optional[ServerCallContext] = None,
    ) -> Task | Message:
        """处理 message/send 方法 - 同步消息处理"""
        app_logger.info(f"[A2A Handler] 收到 message/send 请求")

        message = params.message

        # 提取文本内容
        text_parts = []
        for part in message.parts:
            if hasattr(part, 'root') and hasattr(part.root, 'text'):
                text_parts.append(part.root.text)
            elif hasattr(part, 'text'):
                text_parts.append(part.text)

        if not text_parts:
            # 返回错误消息
            return Message(
                role=Role.agent,
                parts=[TextPart(text="错误: 消息中没有文本内容")],
                message_id=str(uuid.uuid4()),
                context_id=message.context_id or str(uuid.uuid4()),
            )

        question = text_parts[0]
        session_id = message.context_id or str(uuid.uuid4())

        app_logger.info(f"[A2A Handler] 问题: {question[:100]}...")
        app_logger.info(f"[A2A Handler] 会话ID: {session_id}")

        # 获取对话图
        chat_graph = get_chat_graph()

        # 创建状态
        state = create_chat_state(
            messages=[HumanMessage(content=question)],
            session_id=session_id
        )

        config = {"configurable": {"thread_id": session_id}}

        try:
            # 同步调用对话图
            result = await chat_graph.ainvoke(state, config=config)

            # 提取回答
            answer = "抱歉，我无法生成响应。"
            messages = result.get("messages") if isinstance(result, dict) else None
            if messages:
                from langchain_core.messages import AIMessage
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage):
                        answer = msg.content
                        break

            # 返回 Message 对象
            return Message(
                role=Role.agent,
                parts=[TextPart(text=answer)],
                message_id=str(uuid.uuid4()),
                context_id=session_id,
            )

        except Exception as e:
            app_logger.error(f"[A2A Handler] 处理失败: {e}")
            return Message(
                role=Role.agent,
                parts=[TextPart(text=f"错误: {str(e)}")],
                message_id=str(uuid.uuid4()),
                context_id=session_id,
            )


    async def on_message_send_stream(
        self,
        params: MessageSendParams,
        context: Optional[ServerCallContext] = None,
    ) -> AsyncGenerator[Event, None]:
        """处理 message/stream 方法 - 流式消息处理"""
        app_logger.info(f"[A2A Handler] 收到 message/stream 请求")

        message = params.message

        # 提取文本内容
        text_parts = []
        for part in message.parts:
            if hasattr(part, 'root') and hasattr(part.root, 'text'):
                text_parts.append(part.root.text)
            elif hasattr(part, 'text'):
                text_parts.append(part.text)

        if not text_parts:
            # 返回错误事件
            task_id = str(uuid.uuid4())
            context_id = message.context_id or str(uuid.uuid4())

            yield TaskStatusUpdateEvent(
                taskId=task_id,
                contextId=context_id,
                final=True,
                status=TaskStatus(state=TaskState.failed),
            )
            return

        question = text_parts[0]
        session_id = message.context_id or str(uuid.uuid4())
        task_id = str(uuid.uuid4())

        app_logger.info(f"[A2A Handler] 流式问题: {question[:100]}...")
        app_logger.info(f"[A2A Handler] 会话ID: {session_id}")
        app_logger.info(f"[A2A Handler] 任务ID: {task_id}")

        # 存储任务
        self.tasks[task_id] = {
            "id": task_id,
            "context_id": session_id,
            "state": TaskState.working,
        }

        try:
            # 将用户消息封装为 LangChain HumanMessage
            messages = [HumanMessage(content=question)]

            # 使用流式调用
            answer_parts = []
            async for token in stream_graph("a2a-chat", messages, session_id):
                if not token:
                    continue

                answer_parts.append(token)

                # 生成流式事件 - 中间状态
                yield TaskStatusUpdateEvent(
                    taskId=task_id,
                    contextId=session_id,
                    final=False,
                    status=TaskStatus(
                        state=TaskState.working,
                        message=Message(
                            role=Role.agent,
                            parts=[TextPart(text=token)],
                            messageId=str(uuid.uuid4()),
                            contextId=session_id,
                        ),
                    ),
                )

            # 发送最终完成事件
            full_answer = "".join(answer_parts) if answer_parts else ""

            self.tasks[task_id]["state"] = TaskState.completed

            yield TaskStatusUpdateEvent(
                taskId=task_id,
                contextId=session_id,
                final=True,
                status=TaskStatus(
                    state=TaskState.completed,
                    message=Message(
                        role=Role.agent,
                        parts=[TextPart(text=full_answer)],
                        messageId=str(uuid.uuid4()),
                        contextId=session_id,
                    ),
                ),
            )

        except Exception as e:
            app_logger.error(f"[A2A Handler] 流式处理失败: {e}")

            self.tasks[task_id]["state"] = TaskState.failed

            yield TaskStatusUpdateEvent(
                taskId=task_id,
                contextId=session_id,
                final=True,
                status=TaskStatus(
                    state=TaskState.failed,
                    message=Message(
                        role=Role.agent,
                        parts=[TextPart(text=f"错误: {str(e)}")],
                        messageId=str(uuid.uuid4()),
                        contextId=session_id,
                    ),
                ),
            )


    async def on_get_task(
        self,
        params: TaskQueryParams,
        context: Optional[ServerCallContext] = None,
    ) -> Task | None:
        """处理 tasks/get 方法"""
        app_logger.info(f"[A2A Handler] 收到 tasks/get 请求: {params.id}")

        task_data = self.tasks.get(params.id)
        if not task_data:
            return None

        return Task(
            id=task_data["id"],
            contextId=task_data["context_id"],
            status=TaskStatus(state=task_data["state"]),
        )

    async def on_cancel_task(
        self,
        params: TaskIdParams,
        context: Optional[ServerCallContext] = None,
    ) -> Task | None:
        """处理 tasks/cancel 方法"""
        app_logger.info(f"[A2A Handler] 收到 tasks/cancel 请求: {params.id}")

        task_data = self.tasks.get(params.id)
        if not task_data:
            return None

        # 更新任务状态为已取消
        task_data["state"] = TaskState.canceled

        return Task(
            id=task_data["id"],
            contextId=task_data["context_id"],
            status=TaskStatus(state=TaskState.canceled),
        )

    async def on_set_task_push_notification_config(
        self,
        params: TaskPushNotificationConfig,
        context: Optional[ServerCallContext] = None,
    ) -> TaskPushNotificationConfig:
        """处理 tasks/pushNotificationConfig/set 方法"""
        app_logger.info(f"[A2A Handler] 收到 pushNotificationConfig/set 请求")
        # 简单返回相同配置
        return params

    async def on_get_task_push_notification_config(
        self,
        params: TaskIdParams,
        context: Optional[ServerCallContext] = None,
    ) -> TaskPushNotificationConfig | None:
        """处理 tasks/pushNotificationConfig/get 方法"""
        app_logger.info(f"[A2A Handler] 收到 pushNotificationConfig/get 请求")
        # 当前不支持，返回 None
        return None

    async def on_delete_task_push_notification_config(
        self,
        params: TaskIdParams,
        context: Optional[ServerCallContext] = None,
    ) -> bool:
        """处理 tasks/pushNotificationConfig/delete 方法"""
        app_logger.info(f"[A2A Handler] 收到 pushNotificationConfig/delete 请求")
        # 当前不支持，返回 False
        return False

    async def on_list_task_push_notification_config(
        self,
        context: Optional[ServerCallContext] = None,
    ) -> list[TaskPushNotificationConfig]:
        """处理 tasks/pushNotificationConfig/list 方法"""
        app_logger.info(f"[A2A Handler] 收到 pushNotificationConfig/list 请求")
        # 当前不支持，返回空列表
        return []

    async def on_resubscribe_to_task(
        self,
        params: TaskIdParams,
        context: Optional[ServerCallContext] = None,
    ) -> AsyncGenerator[Event, None]:
        """处理 tasks/resubscribe 方法"""
        app_logger.info(f"[A2A Handler] 收到 tasks/resubscribe 请求")
        # 当前不支持，返回空生成器
        return
        yield  # 使其成为生成器


# 创建全局请求处理器实例
_request_handler = A2ARequestHandler()


def get_a2a_request_handler() -> A2ARequestHandler:
    """获取 A2A 请求处理器实例"""
    return _request_handler

