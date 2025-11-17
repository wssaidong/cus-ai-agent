"""A2A JSON-RPC 入口路由

提供基于 A2A 协议的 JSON-RPC 2.0 调用入口，
目前实现核心方法：message/send、tasks/get、tasks/cancel。
"""
from typing import Any, Dict, List, Optional, Union
import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field, ValidationError
from typing import Literal
from langchain_core.messages import HumanMessage, AIMessage

from src.agent.multi_agent.chat_graph import get_chat_graph
from src.agent.multi_agent.chat_state import create_chat_state
from src.utils import app_logger


router = APIRouter(prefix="/a2a", tags=["A2A RPC"])


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


@router.post("/v1")
async def a2a_jsonrpc_endpoint(request: JSONRPCRequest) -> Dict[str, Any]:
    """A2A JSON-RPC 统一入口，仅支持 JSON-RPC 2.0。"""
    if request.jsonrpc != "2.0":
        return _jsonrpc_error(request.id, -32600, "Invalid Request", {"reason": "jsonrpc 必须为 '2.0'"})

    try:
        if request.method == "message/send":
            return await _handle_message_send(request)
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

