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
from langchain_openai import ChatOpenAI
from src.utils import app_logger
from src.agent import agent_graph, AgentState
from src.agent.nodes import create_dynamic_agent_executor
from src.agent.memory import get_memory_manager
from src.config import settings
from .models import (
    ChatRequest, ChatResponse, HealthResponse, ErrorResponse,
    CompletionRequest, CompletionResponse, CompletionChoice,
    CompletionUsage, Message, CompletionStreamChunk
)


router = APIRouter(prefix="/api/v1", tags=["智能体"])


@router.post("/chat", response_model=ChatResponse, summary="普通对话接口")
async def chat(request: ChatRequest) -> ChatResponse:
    """
    普通对话接口

    - **message**: 用户消息内容
    - **session_id**: 会话ID（可选）
    - **config**: 配置参数（可选）
    """
    try:
        start_time = time.time()

        # 生成会话ID
        session_id = request.session_id or str(uuid.uuid4())

        # 初始化状态
        initial_state: AgentState = {
            "messages": [HumanMessage(content=request.message)],
            "intermediate_steps": [],
            "tool_results": [],
            "final_response": None,
            "metadata": {
                "session_id": session_id,
                "start_time": start_time,
            },
            "iteration": 0,
            "is_finished": False,
        }

        # 执行智能体 - 传递 thread_id 配置以支持 checkpointer
        config = {"configurable": {"thread_id": session_id}}
        result = agent_graph.invoke(initial_state, config=config)

        # 计算执行时间
        execution_time = time.time() - start_time

        # 构建响应
        response = ChatResponse(
            response=result.get("final_response", "抱歉，我无法生成响应。"),
            session_id=session_id,
            metadata={
                "execution_time": round(execution_time, 2),
                "llm_calls": result.get("metadata", {}).get("llm_calls", 0),
                "tool_calls": len(result.get("intermediate_steps", [])),
            }
        )

        return response

    except Exception as e:
        app_logger.error(f"聊天请求失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream", summary="流式对话接口")
async def chat_stream(request: ChatRequest):
    """
    流式对话接口（Server-Sent Events）

    - **message**: 用户消息内容
    - **session_id**: 会话ID（可选）
    - **config**: 配置参数（可选）
    """

    async def generate() -> AsyncIterator[str]:
        """生成流式响应"""
        try:
            start_time = time.time()

            # 生成会话ID
            session_id = request.session_id or str(uuid.uuid4())

            # 发送开始事件
            yield f"data: {{'type': 'start', 'session_id': '{session_id}'}}\n\n"

            # 初始化状态
            initial_state: AgentState = {
                "messages": [HumanMessage(content=request.message)],
                "intermediate_steps": [],
                "tool_results": [],
                "final_response": None,
                "metadata": {
                    "session_id": session_id,
                    "start_time": start_time,
                },
                "iteration": 0,
                "is_finished": False,
            }

            # 流式执行智能体 - 传递 thread_id 配置以支持 checkpointer
            config = {"configurable": {"thread_id": session_id}}
            async for event in agent_graph.astream(initial_state, config=config):
                # 发送中间事件
                if "llm" in event:
                    node_output = event["llm"]
                    if node_output.get("final_response"):
                        yield f"data: {{'type': 'token', 'content': '{node_output['final_response']}'}}\n\n"

            # 计算执行时间
            execution_time = time.time() - start_time

            # 发送完成事件
            yield f"data: {{'type': 'end', 'execution_time': {execution_time:.2f}}}\n\n"

        except Exception as e:
            app_logger.error(f"流式聊天请求失败: {str(e)}")
            yield f"data: {{'type': 'error', 'message': '{str(e)}'}}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
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
    OpenAI兼容的Chat Completions接口

    支持标准的OpenAI API格式，可以直接替换OpenAI API使用
    支持流式和非流式输出（通过stream参数控制）

    - **model**: 模型名称
    - **messages**: 消息列表（支持system、user、assistant角色）
    - **temperature**: 温度参数（0-2）
    - **max_tokens**: 最大生成token数
    - **stream**: 是否流式输出（默认false）
    """

    # 如果请求流式输出，返回流式响应
    if request.stream:
        return await _chat_completions_stream(request)
    else:
        return await _chat_completions_normal(request)


async def _chat_completions_normal(request: CompletionRequest) -> CompletionResponse:
    """非流式Completions响应 - 使用智能体或多智能体"""
    try:
        start_time = time.time()
        request_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"

        # 提取用户消息和系统消息
        user_messages = []
        system_messages = []

        for msg in request.messages:
            if msg.role == "user":
                user_messages.append(msg.content)
            elif msg.role == "system":
                system_messages.append(msg.content)

        # 合并消息
        input_text = "\n".join(user_messages)

        # 如果有系统消息，添加到输入前面
        if system_messages:
            input_text = "\n".join(system_messages) + "\n\n" + input_text

        # 判断是否使用多智能体
        if request.use_multi_agent:
            # 使用多智能体系统
            from src.agent.multi_agent.multi_agent_state import create_initial_state
            from src.agent.multi_agent.multi_agent_graph import multi_agent_graph

            # 构建任务
            task = {
                "description": input_text,
                "type": "chat_completion",
                "context": "\n".join(system_messages) if system_messages else None,
            }

            # 生成 session_id (使用 user 参数或生成新的)
            session_id = request.user or f"session-{request_id}"

            # 创建初始状态
            initial_state = create_initial_state(
                task=task,
                session_id=session_id,
                coordination_mode=request.coordination_mode,
                max_iterations=request.max_iterations,
                max_feedback_rounds=request.max_feedback_rounds,
            )

            # 执行多智能体协作 (必须提供 thread_id)
            config = {"configurable": {"thread_id": session_id}}

            result = await multi_agent_graph.ainvoke(initial_state, config=config)

            # 提取最终结果
            final_result = result.get("final_result", {})
            response_content = final_result.get("summary", final_result.get("output", "抱歉，我无法生成响应。"))

        else:
            # 使用单智能体
            # 创建动态智能体执行器（使用请求中的参数）
            agent_executor = create_dynamic_agent_executor(
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )

            # 调用智能体
            result = await agent_executor.ainvoke({"input": input_text})

            # 获取响应内容
            response_content = result.get("output", "抱歉，我无法生成响应。")

        # 计算token使用（简单估算）
        prompt_text = "\n".join([msg.content for msg in request.messages])
        prompt_tokens = _estimate_tokens(prompt_text)
        completion_tokens = _estimate_tokens(response_content)
        total_tokens = prompt_tokens + completion_tokens

        # 构建OpenAI格式的响应
        completion_response = CompletionResponse(
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

        return completion_response

    except Exception as e:
        app_logger.error(f"Completions请求失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def _chat_completions_stream(request: CompletionRequest):
    """流式Completions响应 - 使用智能体或多智能体（流式输出）"""

    async def generate() -> AsyncIterator[str]:
        """生成流式响应"""
        try:
            start_time = time.time()
            request_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"

            # 构建输入消息
            user_messages = []
            system_messages = []

            for msg in request.messages:
                if msg.role == "user":
                    user_messages.append(msg.content)
                elif msg.role == "system":
                    system_messages.append(msg.content)

            input_text = "\n".join(user_messages)
            if system_messages:
                input_text = "\n".join(system_messages) + "\n\n" + input_text

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

            # 判断是否使用多智能体
            if request.use_multi_agent:
                # 使用多智能体系统（流式输出）
                from src.agent.multi_agent.multi_agent_state import create_initial_state
                from src.agent.multi_agent.multi_agent_graph import multi_agent_graph

                # 构建任务
                task = {
                    "description": input_text,
                    "type": "chat_completion",
                    "context": "\n".join(system_messages) if system_messages else None,
                }

                # 生成 session_id (使用 user 参数或生成新的)
                session_id = request.user or f"session-{request_id}"

                # 创建初始状态
                initial_state = create_initial_state(
                    task=task,
                    session_id=session_id,
                    coordination_mode=request.coordination_mode,
                    max_iterations=request.max_iterations,
                    max_feedback_rounds=request.max_feedback_rounds,
                )

                # 执行多智能体协作（流式）- 必须提供 thread_id
                config = {"configurable": {"thread_id": session_id}}

                # 流式输出多智能体执行过程
                async for event in multi_agent_graph.astream(initial_state, config=config):
                    # 提取智能体输出
                    for node_name, node_output in event.items():
                        if isinstance(node_output, dict):
                            # 提取智能体结果
                            agent_results = node_output.get("agent_results", {})
                            for agent_id, result in agent_results.items():
                                if result.get("output"):
                                    content = f"[{result.get('agent_name', agent_id)}]: {result['output'][:100]}...\n"
                                    content_chunk = CompletionStreamChunk(
                                        id=request_id,
                                        object="chat.completion.chunk",
                                        created=int(start_time),
                                        model=request.model,
                                        choices=[{
                                            "index": 0,
                                            "delta": {"content": content},
                                            "finish_reason": None
                                        }]
                                    )
                                    yield f"data: {content_chunk.model_dump_json()}\n\n"

            else:
                # 使用单智能体（流式输出）
                # 创建动态智能体执行器
                agent_executor = create_dynamic_agent_executor(
                    model=request.model,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                )

                # 流式调用智能体
                # AgentExecutor 的 astream_events 支持流式输出
                full_response = ""
                async for event in agent_executor.astream_events(
                    {"input": input_text},
                    version="v1"
                ):
                    kind = event["event"]

                    # 捕获 LLM 的流式输出
                    if kind == "on_chat_model_stream":
                        content = event["data"]["chunk"].content
                        if content:
                            full_response += content
                            # 发送内容块
                            content_chunk = CompletionStreamChunk(
                                id=request_id,
                                object="chat.completion.chunk",
                                created=int(start_time),
                                model=request.model,
                                choices=[{
                                    "index": 0,
                                    "delta": {"content": content},
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
            error_chunk = {
                "error": {
                    "message": str(e),
                    "type": "server_error",
                    "code": 500
                }
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"

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

