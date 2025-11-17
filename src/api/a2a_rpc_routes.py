"""A2A JSON-RPC 入口路由

提供基于 A2A 协议的 JSON-RPC 2.0 调用入口，
目前实现核心方法：message/send、tasks/get、tasks/cancel。
"""
import json
import uuid
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError
from typing import Literal
from langchain_core.messages import HumanMessage, AIMessage

from src.agent.multi_agent.chat_graph import get_chat_graph
from src.agent.multi_agent.chat_state import create_chat_state
from src.api.openai_routes import stream_graph
from src.utils import app_logger


router = APIRouter(prefix="/api/v1/a2a", tags=["A2A RPC"])


class JSONRPCError(BaseModel):
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


class JSONRPCRequest(BaseModel):
    jsonrpc: str = Field("2.0", description="JSON-RPC 版本，仅支持 2.0")
    method: str
    id: Optional[Union[str, int]] = None
    params: Optional[Dict[str, Any]] = None


class TextPart(BaseModel):
    kind: Literal["text"] = "text"
    text: str


class A2AMessage(BaseModel):
    role: str
    parts: List[TextPart]
    messageId: Optional[str] = None
    taskId: Optional[str] = None
    contextId: Optional[str] = None


class MessageSendParams(BaseModel):
    message: A2AMessage
    metadata: Optional[Dict[str, Any]] = None


def _jsonrpc_result(id_value: Optional[Union[str, int]], result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_value, "result": result}


def _jsonrpc_error(
    id_value: Optional[Union[str, int]], code: int, message: str, data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_value, "error": JSONRPCError(code=code, message=message, data=data).model_dump()}


async def _handle_message_send(req: JSONRPCRequest) -> Dict[str, Any]:
    if not isinstance(req.params, dict):
        return _jsonrpc_error(req.id, -32602, "Invalid params", {"reason": "params 必须是对象"})

    try:
        params = MessageSendParams(**req.params)
    except ValidationError as e:
        return _jsonrpc_error(req.id, -32602, "Invalid params", {"errors": e.errors()})

    text_parts = [p for p in params.message.parts if p.kind == "text" and p.text]
    if not text_parts:
        return _jsonrpc_error(req.id, -32602, "Invalid params", {"reason": "message.parts 至少包含一个非空 text"})

    question = text_parts[0].text
    session_id = params.message.contextId or str(uuid.uuid4())

    chat_graph = get_chat_graph()
    state = create_chat_state(messages=[HumanMessage(content=question)], session_id=session_id)
    config = {"configurable": {"thread_id": session_id}}

    try:
        result = await chat_graph.ainvoke(state, config=config)
    except Exception as e:  # pragma: no cover - 防御性日志
        app_logger.error(f"A2A message/send 调用对话图失败: {e}")
        return _jsonrpc_error(req.id, -32603, "Internal error", {"detail": str(e)})

    answer = "抱歉，我无法生成响应。"
    messages = result.get("messages") if isinstance(result, dict) else None
    if messages:
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                answer = msg.content
                break

    message_id = params.message.messageId or str(uuid.uuid4())
    result_obj = {
        "messageId": message_id,
        "contextId": session_id,
        "parts": [{"kind": "text", "text": answer}],
        "kind": "message",
        "metadata": params.metadata or {},
    }
    return _jsonrpc_result(req.id, result_obj)


def _build_streaming_response(
    req: JSONRPCRequest,
    generator,
) -> StreamingResponse:
    """包装 SSE StreamingResponse，生成 JSON-RPC 响应流。

    注意：A2A 规范要求 SSE 的每条 data 都是 JSON-RPC Response 对象。
    """

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用反向代理缓冲
            "Connection": "keep-alive",
        },
    )


def _build_streaming_error_response(
    req: JSONRPCRequest,
    code: int,
    message: str,
    data: Optional[Dict[str, Any]] = None,
) -> StreamingResponse:
    """将 JSON-RPC 错误包装为 SSE 流（单条 error + DONE）。"""

    error_obj = _jsonrpc_error(req.id, code, message, data)

    async def error_stream():
        yield f"data: {json.dumps(error_obj, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return _build_streaming_response(req, error_stream())


def _handle_message_stream(req: JSONRPCRequest) -> StreamingResponse:
    """A2A message/stream 实现：使用 SSE 推送 JSON-RPC 响应流。

    - HTTP 层返回 text/event-stream
    - 每条 SSE data 是一个 JSON-RPC Response
    - result 里包含 Task + TaskStatusUpdateEvent 风格的数据（简化实现）
    """

    # 1. 解析参数
    if not isinstance(req.params, dict):
        return _build_streaming_error_response(
            req,
            -32602,
            "Invalid params",
            {"reason": "params 必须是对象"},
        )

    try:
        params = MessageSendParams(**req.params)
    except ValidationError as e:
        return _build_streaming_error_response(
            req,
            -32602,
            "Invalid params",
            {"errors": e.errors()},
        )

    text_parts = [p for p in params.message.parts if p.kind == "text" and p.text]
    if not text_parts:
        return _build_streaming_error_response(
            req,
            -32602,
            "Invalid params",
            {"reason": "message.parts 至少包含一个非空 text"},
        )

    question = text_parts[0].text
    session_id = params.message.contextId or str(uuid.uuid4())
    message_id = params.message.messageId or str(uuid.uuid4())
    task_id = params.message.taskId or str(uuid.uuid4())

    async def event_generator():
        """生成 SSE data: <JSON-RPC Response>\n\n"""

        answer_parts: List[str] = []

        try:
            # 将用户消息封装为 LangChain HumanMessage
            messages = [HumanMessage(content=question)]

            # 使用已有的 stream_graph 对多智能体对话图进行流式调用
            async for token in stream_graph("a2a-chat", messages, session_id):
                if not token:
                    continue

                answer_parts.append(token)

                event = {
                    "type": "TaskStatusUpdateEvent",
                    "taskId": task_id,
                    "state": "working",
                    "final": False,
                    "messageDelta": {
                        "messageId": message_id,
                        "contextId": session_id,
                        "parts": [
                            {"kind": "text", "text": token},
                        ],
                    },
                }

                result_obj = {
                    "task": {
                        "id": task_id,
                        "state": "working",
                        "contextId": session_id,
                    },
                    "events": [event],
                    "final": False,
                    "metadata": params.metadata or {},
                }

                response_obj = _jsonrpc_result(req.id, result_obj)
                yield f"data: {json.dumps(response_obj, ensure_ascii=False)}\n\n"

            # 发送最终完成事件
            full_answer = "".join(answer_parts) if answer_parts else ""

            final_event = {
                "type": "TaskStatusUpdateEvent",
                "taskId": task_id,
                "state": "completed",
                "final": True,
                "message": {
                    "messageId": message_id,
                    "contextId": session_id,
                    "parts": [
                        {"kind": "text", "text": full_answer},
                    ],
                    "kind": "message",
                    "metadata": params.metadata or {},
                },
            }

            final_result = {
                "task": {
                    "id": task_id,
                    "state": "completed",
                    "contextId": session_id,
                },
                "events": [final_event],
                "final": True,
                "metadata": params.metadata or {},
            }

            final_response = _jsonrpc_result(req.id, final_result)
            yield f"data: {json.dumps(final_response, ensure_ascii=False)}\n\n"

        except Exception as e:  # pragma: no cover - 防御性日志
            app_logger.error(f"A2A message/stream 处理异常: {e}")
            error_obj = _jsonrpc_error(
                req.id,
                -32603,
                "Internal error",
                {"detail": str(e)},
            )
            yield f"data: {json.dumps(error_obj, ensure_ascii=False)}\n\n"

        finally:
            # 通知客户端流结束
            yield "data: [DONE]\n\n"

    return _build_streaming_response(req, event_generator())



@router.post("")
async def a2a_jsonrpc_endpoint(request: JSONRPCRequest):
    """A2A JSON-RPC 统一入口，仅支持 JSON-RPC 2.0。

    根据 method 分发到不同的处理函数：
    - message/send  -> 同步 JSON 响应
    - message/stream -> SSE 流式 JSON-RPC 响应
    - tasks/get、tasks/cancel -> 任务相关错误响应（当前为占位实现）
    """
    if request.jsonrpc != "2.0":
        return _jsonrpc_error(request.id, -32600, "Invalid Request", {"reason": "jsonrpc 必须为 '2.0'"})

    try:
        if request.method == "message/send":
            return await _handle_message_send(request)
        if request.method == "message/stream":
            # 注意：返回的是 StreamingResponse（text/event-stream）
            return _handle_message_stream(request)
        if request.method == "tasks/get":
            # 当前实现同步返回，无任务持久化，统一视为未找到
            return _jsonrpc_error(request.id, -32001, "Task not found")
        if request.method == "tasks/cancel":
            return _jsonrpc_error(
                request.id,
                -32002,
                "Task cannot be canceled",
                {"reason": "当前实现不支持任务取消"},
            )
        return _jsonrpc_error(request.id, -32601, "Method not found")
    except Exception as e:  # pragma: no cover - 全局兜底
        app_logger.error(f"A2A JSON-RPC 处理异常: {e}")
        return _jsonrpc_error(request.id, -32603, "Internal error", {"detail": str(e)})

