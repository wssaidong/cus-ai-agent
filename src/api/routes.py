"""
API路由定义
"""
import time
import uuid
import json
from datetime import datetime
from typing import AsyncIterator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from src.utils import app_logger
from src.agent.memory import get_memory_manager
from src.agent.multi_agent.chat_graph import get_chat_graph
from src.agent.multi_agent.chat_state import create_chat_state
from src.config import settings
from .models import (
    ChatRequest, ChatResponse, HealthResponse,
    CompletionRequest, CompletionResponse, CompletionChoice,
    CompletionUsage, Message, CompletionStreamChunk
)


router = APIRouter(prefix="/api/v1", tags=["智能体"])


@router.post("/chat", response_model=ChatResponse, summary="普通对话接口")
async def chat(request: ChatRequest) -> ChatResponse:
    """
    普通对话接口（使用多智能体架构）

    - **message**: 用户消息内容
    - **session_id**: 会话ID（可选）
    - **config**: 配置参数（可选）
    """
    try:
        start_time = time.time()

        # 生成会话ID
        session_id = request.session_id or str(uuid.uuid4())

        # 使用多智能体架构
        chat_graph = get_chat_graph()
        initial_state = create_chat_state(
            messages=[HumanMessage(content=request.message)],
            session_id=session_id,
        )

        config = {"configurable": {"thread_id": session_id}}
        result = await chat_graph.ainvoke(initial_state, config=config)

        # 提取最终响应
        final_response = ""
        if result.get("messages"):
            for msg in reversed(result["messages"]):
                if isinstance(msg, AIMessage):
                    final_response = msg.content
                    break

        # 计算执行时间
        execution_time = time.time() - start_time

        # 构建响应
        response = ChatResponse(
            response=final_response or "抱歉，我无法生成响应。",
            session_id=session_id,
            metadata={
                "execution_time": round(execution_time, 2),
                "architecture": "multi_agent",
            }
        )

        return response

    except Exception as e:
        app_logger.error(f"聊天请求失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream", summary="流式对话接口")
async def chat_stream(request: ChatRequest):
    """
    流式对话接口（Server-Sent Events，使用多智能体架构）

    - **message**: 用户消息内容
    - **session_id**: 会话ID（可选）
    - **config**: 配置参数（可选）

    注意：此接口使用自定义格式，推荐使用 /v1/chat/completions 接口（OpenAI 兼容）
    """

    async def generate() -> AsyncIterator[str]:
        """生成流式响应"""
        try:
            start_time = time.time()
            request_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"

            # 生成会话ID
            session_id = request.session_id or f"session-{request_id}"

            # 发送开始事件
            yield f"data: {{'type': 'start', 'session_id': '{session_id}'}}\n\n"

            # 使用多智能体架构
            chat_graph = get_chat_graph()
            initial_state = create_chat_state(
                messages=[HumanMessage(content=request.message)],
                session_id=session_id,
            )

            config = {"configurable": {"thread_id": session_id}}

            # 用于跟踪节点和内容
            current_node = None
            responder_content_sent = False
            worker_content_sent = set()

            # 使用 astream_events 获取真正的流式输出
            async for event in chat_graph.astream_events(initial_state, config=config, version="v2"):
                kind = event.get("event")

                # 跟踪当前节点
                if kind == "on_chain_start":
                    metadata = event.get("metadata", {})
                    langgraph_node = metadata.get("langgraph_node", "")
                    if langgraph_node:
                        current_node = langgraph_node

                # 捕获 LLM 的流式输出 token
                if kind == "on_chat_model_stream":
                    # 只输出非 Supervisor 节点的内容
                    if current_node and current_node != "supervisor":
                        content = event.get("data", {}).get("chunk", {})

                        # 提取内容
                        if hasattr(content, "content") and content.content:
                            # 标记该节点已发送内容
                            worker_content_sent.add(current_node)

                            # 发送内容
                            content_escaped = content.content.replace("'", "\\'").replace("\n", "\\n")
                            yield f"data: {{'type': 'token', 'content': '{content_escaped}'}}\n\n"

                # 捕获节点完成事件（处理非流式节点）
                if kind == "on_chain_end":
                    metadata = event.get("metadata", {})
                    langgraph_node = metadata.get("langgraph_node", "")

                    # 处理 Responder 节点
                    if langgraph_node == "responder" and not responder_content_sent:
                        output = event.get("data", {}).get("output", {})
                        messages = output.get("messages", [])

                        if messages:
                            last_message = messages[-1]
                            if hasattr(last_message, "content") and last_message.content:
                                content_escaped = last_message.content.replace("'", "\\'").replace("\n", "\\n")
                                yield f"data: {{'type': 'token', 'content': '{content_escaped}'}}\n\n"
                                responder_content_sent = True

                    # 处理 Worker 节点（如果流式输出没有捕获到）
                    worker_nodes = ["search_agent", "write_agent", "analysis_agent", "execution_agent", "quality_agent"]
                    if langgraph_node in worker_nodes and langgraph_node not in worker_content_sent:
                        output = event.get("data", {}).get("output", {})
                        messages = output.get("messages", [])

                        if messages:
                            last_message = messages[-1]
                            if hasattr(last_message, "content") and last_message.content:
                                worker_content_sent.add(langgraph_node)
                                content_escaped = last_message.content.replace("'", "\\'").replace("\n", "\\n")
                                yield f"data: {{'type': 'token', 'content': '{content_escaped}'}}\n\n"

            # 计算执行时间
            execution_time = time.time() - start_time

            # 发送完成事件
            yield f"data: {{'type': 'end', 'execution_time': {execution_time:.2f}}}\n\n"

        except Exception as e:
            app_logger.error(f"流式聊天请求失败: {str(e)}")
            import traceback
            app_logger.error(f"堆栈跟踪:\n{traceback.format_exc()}")

            error_msg = str(e).replace("'", "\\'")
            yield f"data: {{'type': 'error', 'message': '{error_msg}'}}\n\n"
            # 确保发送结束标记
            yield f"data: {{'type': 'end'}}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/health", response_model=HealthResponse, summary="健康检查")
async def health() -> HealthResponse:
    """
    健康检查接口
    """
    return HealthResponse(
        status="healthy",
        version=settings.api_version,
        timestamp=datetime.now().isoformat()
    )


# ==================== OpenAI 兼容接口 ====================

def _convert_messages_to_langchain(messages: list) -> list:
    """将OpenAI格式的消息转换为LangChain格式"""
    langchain_messages = []
    for msg in messages:
        role = msg.role
        content = msg.content

        if role == "system":
            langchain_messages.append(SystemMessage(content=content))
        elif role == "user":
            langchain_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))

    return langchain_messages


def _estimate_tokens(text: str) -> int:
    """估算token数量（简单估算：中文1字=1token，英文1词=1token）"""
    # 简单估算：按字符数除以2
    return len(text) // 2 + len(text.split())


@router.post("/chat/completions", summary="OpenAI兼容的Completions接口")
async def chat_completions(request: CompletionRequest):
    """
    OpenAI兼容的Chat Completions接口（使用多智能体架构）

    支持标准的OpenAI API格式，可以直接替换OpenAI API使用
    支持流式和非流式输出（通过stream参数控制）

    - **model**: 模型名称
    - **messages**: 消息列表（支持system、user、assistant角色）
    - **temperature**: 温度参数（0-2）
    - **max_tokens**: 最大生成token数
    - **stream**: 是否流式输出（默认false）

    注意：
    - 使用 Planner + Executor 多智能体架构
    - 只返回执行者(executor)的最终结果
    - 提供简洁、直接的用户体验
    """

    # 打印请求入参
    app_logger.info("=" * 80)
    app_logger.info("[/chat/completions] 收到请求")
    app_logger.info(f"  - model: {request.model}")
    app_logger.info(f"  - stream: {request.stream}")
    app_logger.info(f"  - temperature: {request.temperature}")
    app_logger.info(f"  - max_tokens: {request.max_tokens}")
    app_logger.info(f"  - session_id: {request.user if request.user else 'auto-generated'}")
    app_logger.info(f"  - messages 数量: {len(request.messages)}")

    # 打印消息详情
    for i, msg in enumerate(request.messages):
        content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
        app_logger.info(f"    [{i}] {msg.role}: {content_preview}")

    app_logger.info("=" * 80)

    # 如果请求流式输出，返回流式响应
    if request.stream:
        return await _chat_completions_stream(request)
    else:
        return await _chat_completions_normal(request)


async def _chat_completions_normal(request: CompletionRequest) -> CompletionResponse:
    """非流式Completions响应 - 使用多智能体架构"""
    try:
        start_time = time.time()
        request_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"

        # 生成 session_id (使用 user 参数或生成新的)
        session_id = request.user or f"session-{request_id}"

        # 转换 OpenAI 格式的消息到 LangChain 格式
        # 将完整的对话历史（system、user、assistant）传递给 Supervisor
        langchain_messages = []
        for msg in request.messages:
            if msg.role == "system":
                langchain_messages.append(SystemMessage(content=msg.content))
            elif msg.role == "user":
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                langchain_messages.append(AIMessage(content=msg.content))

        app_logger.info(f"[/chat/completions] 转换了 {len(langchain_messages)} 条消息传递给 Supervisor")

        # 创建初始状态（包含完整的对话历史，让 Supervisor 能看到完整上下文）
        initial_state = create_chat_state(
            messages=langchain_messages,
            session_id=session_id,
        )

        # 配置 LangGraph (提供 thread_id 以启用记忆)
        config = {"configurable": {"thread_id": session_id}}

        # 获取聊天图并执行（checkpointer 会自动处理历史消息）
        chat_graph = get_chat_graph()
        result = await chat_graph.ainvoke(initial_state, config=config)

        # 提取最后一条 AI 消息作为响应
        response_content = ""
        for msg in reversed(result.get("messages", [])):
            if isinstance(msg, AIMessage):
                response_content = msg.content
                break

        if not response_content:
            response_content = "抱歉，我无法生成响应。"

        # 计算token使用（简单估算）
        prompt_text = "\n".join([msg.content for msg in request.messages])
        prompt_tokens = _estimate_tokens(prompt_text)
        completion_tokens = _estimate_tokens(response_content)
        total_tokens = prompt_tokens + completion_tokens

        # 构建OpenAI格式的响应
        return CompletionResponse(
            id=request_id,
            object="chat.completion",
            created=int(start_time),
            model=request.model,
            choices=[
                CompletionChoice(
                    index=0,
                    message=Message(
                        role="assistant",
                        content=response_content
                    ),
                    finish_reason="stop"
                )
            ],
            usage=CompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens
            )
        )

    except Exception as e:
        app_logger.error(f"Completions请求失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def _chat_completions_stream(request: CompletionRequest):
    """流式Completions响应 - 使用多智能体架构"""

    async def generate() -> AsyncIterator[str]:
        """生成流式响应"""
        try:
            start_time = time.time()
            request_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"

            # 发送开始块
            start_chunk = CompletionStreamChunk(
                id=request_id,
                object="chat.completion.chunk",
                created=int(start_time),
                model=request.model,
                choices=[{
                    "index": 0,
                    "delta": {"role": "assistant", "content": ""},
                    "finish_reason": None
                }]
            )
            yield f"data: {start_chunk.model_dump_json()}\n\n"

            # 生成 session_id (使用 user 参数或生成新的)
            session_id = request.user or f"session-{request_id}"

            # 转换 OpenAI 格式的消息到 LangChain 格式
            # 将完整的对话历史（system、user、assistant）传递给 Supervisor
            langchain_messages = []
            for msg in request.messages:
                if msg.role == "system":
                    langchain_messages.append(SystemMessage(content=msg.content))
                elif msg.role == "user":
                    langchain_messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    langchain_messages.append(AIMessage(content=msg.content))

            app_logger.info(f"[/chat/completions/stream] 转换了 {len(langchain_messages)} 条消息传递给 Supervisor")

            # 创建初始状态（包含完整的对话历史，让 Supervisor 能看到完整上下文）
            initial_state = create_chat_state(
                messages=langchain_messages,
                session_id=session_id,
            )

            # 执行聊天图（流式）
            config = {"configurable": {"thread_id": session_id}}
            chat_graph = get_chat_graph()

            # 使用 astream_events 获取真正的流式输出
            # 这样可以捕获 LLM 的 token 级别的流式输出

            # 用于跟踪是否在 Supervisor 节点中
            current_node = None
            responder_content_sent = False  # 标记 Responder 内容是否已发送
            supervisor_notified = False  # 标记是否已发送 Supervisor 进度提示
            worker_nodes_notified = set()  # 记录已发送进度提示的 Worker 节点
            worker_content_sent = set()  # 记录已发送内容的 Worker 节点（防止重复）

            async for event in chat_graph.astream_events(initial_state, config=config, version="v2"):
                kind = event.get("event")

                # 跟踪当前节点
                if kind == "on_chain_start":
                    metadata = event.get("metadata", {})
                    langgraph_node = metadata.get("langgraph_node", "")
                    if langgraph_node:
                        current_node = langgraph_node
                        app_logger.debug(f"[Stream] 进入节点: {current_node}")

                        # 当进入 Supervisor 节点时，发送进度提示
                        if current_node == "supervisor" and not supervisor_notified:
                            progress_chunk = CompletionStreamChunk(
                                id=request_id,
                                object="chat.completion.chunk",
                                created=int(start_time),
                                model=request.model,
                                choices=[{
                                    "index": 0,
                                    "delta": {"content": ""},
                                    "finish_reason": None
                                }]
                            )
                            yield f"data: {progress_chunk.model_dump_json()}\n\n"
                            supervisor_notified = True
                            app_logger.debug(f"[Stream] 已发送 Supervisor 进度提示")

                        # 当进入 Worker 节点时，发送进度提示（保持连接活跃）
                        worker_nodes = ["search_agent", "write_agent", "analysis_agent", "execution_agent", "quality_agent"]
                        if current_node in worker_nodes and current_node not in worker_nodes_notified:
                            progress_chunk = CompletionStreamChunk(
                                id=request_id,
                                object="chat.completion.chunk",
                                created=int(start_time),
                                model=request.model,
                                choices=[{
                                    "index": 0,
                                    "delta": {"content": ""},
                                    "finish_reason": None
                                }]
                            )
                            yield f"data: {progress_chunk.model_dump_json()}\n\n"
                            worker_nodes_notified.add(current_node)
                            app_logger.debug(f"[Stream] 已发送 {current_node} 进度提示")

                # 捕获 LLM 的流式输出 token
                if kind == "on_chat_model_stream":
                    # 只输出非 Supervisor 节点的内容
                    # Supervisor 节点输出的是 JSON 决策，不应该返回给用户
                    if current_node and current_node != "supervisor":
                        content = event.get("data", {}).get("chunk", {})

                        # 提取内容
                        if hasattr(content, "content") and content.content:
                            # 标记该节点已发送内容（防止在 on_chain_end 时重复发送）
                            worker_content_sent.add(current_node)

                            # 发送内容块
                            content_chunk = CompletionStreamChunk(
                                id=request_id,
                                object="chat.completion.chunk",
                                created=int(start_time),
                                model=request.model,
                                choices=[{
                                    "index": 0,
                                    "delta": {"content": content.content},
                                    "finish_reason": None
                                }]
                            )
                            yield f"data: {content_chunk.model_dump_json()}\n\n"

                # 捕获节点完成事件
                # Responder 和 Worker 节点不调用 LLM 流式输出，需要在节点完成时捕获输出
                if kind == "on_chain_end":
                    metadata = event.get("metadata", {})
                    langgraph_node = metadata.get("langgraph_node", "")

                    # 处理 Responder 节点输出
                    if langgraph_node == "responder" and not responder_content_sent:
                        # 获取 Responder 的输出
                        output = event.get("data", {}).get("output", {})
                        messages = output.get("messages", [])

                        if messages:
                            # 获取最后一条消息的内容
                            last_message = messages[-1]
                            if hasattr(last_message, "content") and last_message.content:
                                app_logger.info(f"[Stream] Responder 输出: {last_message.content[:100]}...")

                                # 将 Responder 的内容作为流式输出发送
                                content_chunk = CompletionStreamChunk(
                                    id=request_id,
                                    object="chat.completion.chunk",
                                    created=int(start_time),
                                    model=request.model,
                                    choices=[{
                                        "index": 0,
                                        "delta": {"content": last_message.content},
                                        "finish_reason": None
                                    }]
                                )
                                yield f"data: {content_chunk.model_dump_json()}\n\n"
                                responder_content_sent = True

                    # 处理 Worker 节点输出（仅当 LLM 流式输出没有捕获到时）
                    # Worker 节点可能使用 ainvoke 而非 astream，导致流式事件无法捕获
                    worker_nodes = ["search_agent", "write_agent", "analysis_agent", "execution_agent", "quality_agent"]
                    if langgraph_node in worker_nodes and langgraph_node not in worker_content_sent:
                        output = event.get("data", {}).get("output", {})
                        messages = output.get("messages", [])

                        if messages:
                            # 获取最后一条消息的内容
                            last_message = messages[-1]
                            if hasattr(last_message, "content") and last_message.content:
                                app_logger.info(f"[Stream] {langgraph_node} 输出 (fallback): {last_message.content[:100]}...")

                                # 标记已发送
                                worker_content_sent.add(langgraph_node)

                                # 将 Worker 的内容作为流式输出发送
                                content_chunk = CompletionStreamChunk(
                                    id=request_id,
                                    object="chat.completion.chunk",
                                    created=int(start_time),
                                    model=request.model,
                                    choices=[{
                                        "index": 0,
                                        "delta": {"content": last_message.content},
                                        "finish_reason": None
                                    }]
                                )
                                yield f"data: {content_chunk.model_dump_json()}\n\n"

            # 发送结束块
            end_chunk = CompletionStreamChunk(
                id=request_id,
                object="chat.completion.chunk",
                created=int(start_time),
                model=request.model,
                choices=[{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            )
            yield f"data: {end_chunk.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            app_logger.error(f"流式Completions请求失败: {str(e)}")
            import traceback
            app_logger.error(f"堆栈跟踪:\n{traceback.format_exc()}")

            error_chunk = {
                "error": {
                    "message": str(e),
                    "type": "server_error",
                    "code": 500
                }
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
            # 确保发送 [DONE] 标记，防止客户端一直等待
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ==========================================
# 记忆管理 API 接口
# ==========================================

@router.get("/memory/sessions", summary="获取所有会话")
async def get_sessions():
    """
    获取所有会话列表

    Returns:
        会话列表
    """
    try:
        memory_manager = get_memory_manager()
        sessions = memory_manager.list_sessions()
        return {
            "status": "success",
            "data": sessions,
            "count": len(sessions)
        }
    except Exception as e:
        app_logger.error(f"获取会话列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/sessions/{session_id}", summary="获取会话记忆")
async def get_session_memory(session_id: str):
    """
    获取指定会话的记忆信息

    Args:
        session_id: 会话ID

    Returns:
        会话记忆信息
    """
    try:
        memory_manager = get_memory_manager()
        memory = memory_manager.get_session_memory(session_id)

        if "error" in memory:
            raise HTTPException(status_code=404, detail=memory["error"])

        return {
            "status": "success",
            "data": memory
        }
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"获取会话记忆失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/memory/sessions/{session_id}", summary="清空会话记忆")
async def clear_session_memory(session_id: str):
    """
    清空指定会话的记忆

    Args:
        session_id: 会话ID

    Returns:
        清空结果
    """
    try:
        memory_manager = get_memory_manager()
        success = memory_manager.clear_session_memory(session_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")

        return {
            "status": "success",
            "message": f"已清空会话 {session_id} 的记忆"
        }
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"清空会话记忆失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/memory/all", summary="清空所有记忆")
async def clear_all_memory():
    """
    清空所有会话的记忆

    Returns:
        清空结果
    """
    try:
        memory_manager = get_memory_manager()
        count = memory_manager.clear_all_memory()

        return {
            "status": "success",
            "message": f"已清空所有记忆，共 {count} 个会话"
        }
    except Exception as e:
        app_logger.error(f"清空所有记忆失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/stats", summary="获取记忆统计")
async def get_memory_stats():
    """
    获取记忆统计信息

    Returns:
        统计信息
    """
    try:
        memory_manager = get_memory_manager()
        stats = memory_manager.get_memory_stats()

        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        app_logger.error(f"获取记忆统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/export/{session_id}", summary="导出会话记忆")
async def export_session_memory(session_id: str):
    """
    导出指定会话的记忆数据

    Args:
        session_id: 会话ID

    Returns:
        导出的记忆数据
    """
    try:
        memory_manager = get_memory_manager()
        memory_data = memory_manager.export_session_memory(session_id)

        if "error" in memory_data:
            raise HTTPException(status_code=404, detail=memory_data["error"])

        return {
            "status": "success",
            "data": memory_data
        }
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"导出会话记忆失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

