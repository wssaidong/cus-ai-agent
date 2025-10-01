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
        app_logger.info(f"收到聊天请求: {request.message[:50]}...")
        
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
        
        # 执行智能体
        result = agent_graph.invoke(initial_state)
        
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
        
        app_logger.info(f"聊天请求完成，耗时: {execution_time:.2f}秒")
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
            app_logger.info(f"收到流式聊天请求: {request.message[:50]}...")
            
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
            
            # 流式执行智能体
            async for event in agent_graph.astream(initial_state):
                # 发送中间事件
                if "llm" in event:
                    node_output = event["llm"]
                    if node_output.get("final_response"):
                        yield f"data: {{'type': 'token', 'content': '{node_output['final_response']}'}}\n\n"
            
            # 计算执行时间
            execution_time = time.time() - start_time
            
            # 发送完成事件
            yield f"data: {{'type': 'end', 'execution_time': {execution_time:.2f}}}\n\n"
            
            app_logger.info(f"流式聊天请求完成，耗时: {execution_time:.2f}秒")
            
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
    """非流式Completions响应 - 使用智能体"""
    try:
        start_time = time.time()
        request_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"

        app_logger.info(f"收到Completions请求: {request_id}, 模型: {request.model}")

        # 创建动态智能体执行器（使用请求中的参数）
        agent_executor = create_dynamic_agent_executor(
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        # 构建输入消息
        # 提取用户消息
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

        # 调用智能体
        app_logger.info(f"调用智能体: {request.model}")
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

        execution_time = time.time() - start_time
        app_logger.info(f"Completions请求完成: {request_id}, 耗时: {execution_time:.2f}秒")

        return completion_response

    except Exception as e:
        app_logger.error(f"Completions请求失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def _chat_completions_stream(request: CompletionRequest):
    """流式Completions响应 - 使用智能体（流式输出）"""

    async def generate() -> AsyncIterator[str]:
        """生成流式响应"""
        try:
            start_time = time.time()
            request_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"

            app_logger.info(f"收到流式Completions请求: {request_id}, 模型: {request.model}")

            # 创建动态智能体执行器
            agent_executor = create_dynamic_agent_executor(
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )

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

            # 流式调用智能体
            app_logger.info(f"流式调用智能体: {request.model}")

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

            execution_time = time.time() - start_time
            app_logger.info(f"流式Completions请求完成: {request_id}, 耗时: {execution_time:.2f}秒")

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

