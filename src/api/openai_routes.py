"""
OpenAI 兼容 API 路由

提供与 OpenAI API 兼容的接口，支持标准的 OpenAI SDK 访问
"""
import time
import uuid
from typing import AsyncIterator, List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.utils import app_logger
from src.agent.multi_agent.chat_graph import get_chat_graph
from src.agent.multi_agent.chat_state import create_chat_state


router = APIRouter(prefix="/api/v1", tags=["OpenAI 兼容 API"])


# ==========================================
# 数据模型
# ==========================================

class OpenAIMessage(BaseModel):
    """OpenAI 消息格式"""
    role: str = Field(..., description="角色: system, user, assistant")
    content: str = Field(..., description="消息内容")


class OpenAIChatRequest(BaseModel):
    """OpenAI 聊天请求"""
    model: str = Field(..., description="模型名称")
    messages: List[OpenAIMessage] = Field(..., description="消息列表")
    stream: bool = Field(default=True, description="是否流式输出")
    temperature: Optional[float] = Field(default=0.7, description="温度参数")
    max_tokens: Optional[int] = Field(default=None, description="最大 token 数")


class OpenAIChoice(BaseModel):
    """OpenAI 选择"""
    index: int
    message: OpenAIMessage
    finish_reason: str = "stop"


class OpenAIUsage(BaseModel):
    """OpenAI 使用统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class OpenAIChatResponse(BaseModel):
    """OpenAI 聊天响应"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[OpenAIChoice]
    usage: OpenAIUsage


class OpenAIDelta(BaseModel):
    """OpenAI 流式增量"""
    role: Optional[str] = None
    content: Optional[str] = None


class OpenAIStreamChoice(BaseModel):
    """OpenAI 流式选择"""
    index: int
    delta: OpenAIDelta
    finish_reason: Optional[str] = None


class OpenAIStreamChunk(BaseModel):
    """OpenAI 流式响应块"""
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[OpenAIStreamChoice]


class OpenAIModel(BaseModel):
    """OpenAI 模型信息"""
    id: str
    object: str = "model"
    created: int = int(time.time())
    owned_by: str = "cus-ai-agent"


class OpenAIModelList(BaseModel):
    """OpenAI 模型列表"""
    object: str = "list"
    data: List[OpenAIModel]


# ==========================================
# 辅助函数
# ==========================================

def convert_to_langchain_messages(messages: List[OpenAIMessage]) -> List:
    """将 OpenAI 消息格式转换为 LangChain 消息格式"""
    langchain_messages = []
    for msg in messages:
        if msg.role == "system":
            langchain_messages.append(SystemMessage(content=msg.content))
        elif msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_messages.append(AIMessage(content=msg.content))
    return langchain_messages


async def invoke_graph(
    model_name: str,
    messages: List,
    session_id: str
) -> str:
    """调用图并获取响应"""
    # 获取图
    graph = get_chat_graph()

    # 创建状态
    state = create_chat_state(messages=messages, session_id=session_id)

    # 调用图
    config = {"configurable": {"thread_id": session_id}}
    result = await graph.ainvoke(state, config=config)

    # 提取响应
    if result.get("messages"):
        last_message = result["messages"][-1]
        return last_message.content

    return "抱歉，我无法生成响应。"


async def stream_graph(
    model_name: str,
    messages: List,
    session_id: str
) -> AsyncIterator[str]:
    """
    流式调用图 - 使用 stream_mode="messages" 捕获真实的 LLM token 流

    策略：
    1. 使用 graph.astream() 配合 stream_mode="messages"
    2. 自动捕获所有 LLM 的流式输出 token（即使使用 .invoke()）
    3. 通过 metadata 过滤，只输出 Worker Agent 和 Responder 的内容，跳过 Supervisor

    参考：https://docs.langchain.com/oss/python/langgraph/streaming
    """
    from src.utils import app_logger

    # 获取图
    graph = get_chat_graph()

    # 创建状态
    state = create_chat_state(messages=messages, session_id=session_id)

    # 流式调用图
    config = {"configurable": {"thread_id": session_id}}

    from langchain_core.messages import AIMessageChunk

    app_logger.info(f"[StreamGraph] 开始流式输出，session_id={session_id}")

    token_count = 0
    current_node = None

    # 使用 stream_mode="messages" 捕获 LLM 的流式输出
    # 返回 (message_chunk, metadata) 元组
    async for msg, metadata in graph.astream(
        state,
        config=config,
        stream_mode="messages"
    ):
        # 获取当前节点名称
        langgraph_node = metadata.get("langgraph_node", "")

        # 跟踪节点切换
        if langgraph_node and langgraph_node != current_node:
            current_node = langgraph_node
            app_logger.info(f"[StreamGraph] 进入节点: {current_node}")

        # 只输出非 Supervisor 节点的内容
        # Worker Agents: search_agent, write_agent, analysis_agent, execution_agent, quality_agent
        # Responder: responder
        if langgraph_node in ["responder", "search_agent", "write_agent", "analysis_agent", "execution_agent", "quality_agent"]:
            # 只处理 AIMessageChunk（流式 token），跳过完整的 AIMessage
            if isinstance(msg, AIMessageChunk) and hasattr(msg, "content") and msg.content:
                token_count += 1
                # 直接发送 token，无延迟
                yield msg.content

    app_logger.info(f"[StreamGraph] 流式输出完成，共发送 {token_count} 个 token")


# ==========================================
# API 端点
# ==========================================

@router.post("/chat/completions")
async def chat_completions(request: OpenAIChatRequest):
    """
    OpenAI 兼容的聊天完成接口

    支持流式和非流式输出
    """
    try:
        # 转换消息格式
        langchain_messages = convert_to_langchain_messages(request.messages)

        # 生成会话 ID
        session_id = str(uuid.uuid4())

        # 流式输出
        if request.stream:
            async def generate_stream():
                chunk_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
                created = int(time.time())

                # 发送初始块（角色信息）
                initial_chunk = OpenAIStreamChunk(
                    id=chunk_id,
                    created=created,
                    model=request.model,
                    choices=[
                        OpenAIStreamChoice(
                            index=0,
                            delta=OpenAIDelta(role="assistant"),
                            finish_reason=None
                        )
                    ]
                )
                yield f"data: {initial_chunk.model_dump_json()}\n\n"

                # 流式生成内容
                async for content in stream_graph(request.model, langchain_messages, session_id):
                    chunk = OpenAIStreamChunk(
                        id=chunk_id,
                        created=created,
                        model=request.model,
                        choices=[
                            OpenAIStreamChoice(
                                index=0,
                                delta=OpenAIDelta(content=content),
                                finish_reason=None
                            )
                        ]
                    )
                    yield f"data: {chunk.model_dump_json()}\n\n"

                # 发送结束块
                final_chunk = OpenAIStreamChunk(
                    id=chunk_id,
                    created=created,
                    model=request.model,
                    choices=[
                        OpenAIStreamChoice(
                            index=0,
                            delta=OpenAIDelta(),
                            finish_reason="stop"
                        )
                    ]
                )
                yield f"data: {final_chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
                    "Connection": "keep-alive",
                }
            )

        # 非流式输出
        else:
            content = await invoke_graph(request.model, langchain_messages, session_id)

            response = OpenAIChatResponse(
                id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
                created=int(time.time()),
                model=request.model,
                choices=[
                    OpenAIChoice(
                        index=0,
                        message=OpenAIMessage(role="assistant", content=content),
                        finish_reason="stop"
                    )
                ],
                usage=OpenAIUsage(
                    prompt_tokens=0,  # 简化实现，不计算 token
                    completion_tokens=0,
                    total_tokens=0
                )
            )

            return response

    except Exception as e:
        app_logger.error(f"聊天完成错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models():
    """
    列出所有可用的模型

    注意：由于不再限制模型名称，此接口返回空列表。
    客户端可以使用任意模型名称。
    """
    return OpenAIModelList(data=[])


@router.get("/models/{model_id}")
async def retrieve_model(model_id: str):
    """获取单个模型信息"""
    return OpenAIModel(id=model_id)

