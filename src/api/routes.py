"""
API路由定义
"""
import time
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, AIMessage
from src.utils import app_logger
from src.agent.memory import get_memory_manager
from src.agent.multi_agent.chat_graph import get_chat_graph
from src.agent.multi_agent.chat_state import create_chat_state
from src.config import settings
from .models import ChatRequest, ChatResponse, HealthResponse


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

