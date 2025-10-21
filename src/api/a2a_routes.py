"""
A2A 注册中心 API 路由
提供 AgentCard 管理的 REST API 端点
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.config import settings
from src.utils.a2a_agent_card import AgentCardManager
from src.utils import app_logger


# 创建路由
router = APIRouter(prefix="/api/v1/a2a", tags=["A2A 注册中心"])

# 全局 AgentCardManager 实例
_agent_card_manager: Optional[AgentCardManager] = None


def get_agent_card_manager() -> AgentCardManager:
    """获取 AgentCardManager 实例"""
    global _agent_card_manager
    if _agent_card_manager is None:
        _agent_card_manager = AgentCardManager(
            nacos_server=settings.a2a_server_addresses,
            namespace=settings.a2a_namespace,
        )
    return _agent_card_manager


# 请求/响应模型
class AgentCardRequest(BaseModel):
    """AgentCard 创建请求"""
    name: str
    description: str
    version: str = "1.0.0"
    url: Optional[str] = None
    protocol_version: str = "0.2.9"
    preferred_transport: str = "JSONRPC"
    registration_type: str = "SERVICE"
    capabilities: Optional[Dict[str, Any]] = None
    skills: Optional[List[Dict[str, Any]]] = None
    provider: Optional[Dict[str, str]] = None
    icon_url: Optional[str] = None


class AgentCardResponse(BaseModel):
    """AgentCard 响应"""
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


# API 端点

@router.post("/agent-cards", response_model=AgentCardResponse)
async def create_agent_card(request: AgentCardRequest) -> AgentCardResponse:
    """
    创建 AgentCard

    Args:
        request: AgentCard 创建请求

    Returns:
        AgentCardResponse: 创建结果
    """
    try:
        manager = get_agent_card_manager()
        success = manager.create_agent_card(
            name=request.name,
            description=request.description,
            version=request.version,
            url=request.url,
            protocol_version=request.protocol_version,
            preferred_transport=request.preferred_transport,
            registration_type=request.registration_type,
            capabilities=request.capabilities,
            skills=request.skills,
            provider=request.provider,
            icon_url=request.icon_url,
        )

        if success:
            return AgentCardResponse(
                code=0,
                message="success",
                data={"name": request.name, "version": request.version},
            )
        else:
            return AgentCardResponse(
                code=1,
                message="Failed to create AgentCard",
            )

    except Exception as e:
        app_logger.error(f"创建 AgentCard 异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-cards/{agent_name}", response_model=AgentCardResponse)
async def get_agent_card(
    agent_name: str,
    version: Optional[str] = Query(None),
    registration_type: str = Query("SERVICE"),
) -> AgentCardResponse:
    """
    获取 AgentCard 详情

    Args:
        agent_name: AgentCard 名称
        version: 版本号（可选）
        registration_type: 注册类型

    Returns:
        AgentCardResponse: AgentCard 详情
    """
    try:
        manager = get_agent_card_manager()
        data = manager.get_agent_card(
            agent_name=agent_name,
            version=version,
            registration_type=registration_type,
        )

        if data:
            return AgentCardResponse(
                code=0,
                message="success",
                data=data,
            )
        else:
            return AgentCardResponse(
                code=1,
                message="AgentCard not found",
            )

    except Exception as e:
        app_logger.error(f"获取 AgentCard 异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-cards", response_model=AgentCardResponse)
async def list_agent_cards(
    page_no: int = Query(1),
    page_size: int = Query(100),
    agent_name: Optional[str] = Query(None),
    search: str = Query("blur"),
) -> AgentCardResponse:
    """
    列出 AgentCard

    Args:
        page_no: 页码
        page_size: 每页条数
        agent_name: AgentCard 名称（可选）
        search: 搜索类型

    Returns:
        AgentCardResponse: AgentCard 列表
    """
    try:
        manager = get_agent_card_manager()
        data = manager.list_agent_cards(
            page_no=page_no,
            page_size=page_size,
            agent_name=agent_name,
            search=search,
        )

        if data:
            return AgentCardResponse(
                code=0,
                message="success",
                data=data,
            )
        else:
            return AgentCardResponse(
                code=1,
                message="Failed to list AgentCards",
            )

    except Exception as e:
        app_logger.error(f"列出 AgentCard 异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/agent-cards/{agent_name}", response_model=AgentCardResponse)
async def delete_agent_card(
    agent_name: str,
    version: Optional[str] = Query(None),
) -> AgentCardResponse:
    """
    删除 AgentCard

    Args:
        agent_name: AgentCard 名称
        version: 版本号（可选）

    Returns:
        AgentCardResponse: 删除结果
    """
    try:
        manager = get_agent_card_manager()
        success = manager.delete_agent_card(
            agent_name=agent_name,
            version=version,
        )

        if success:
            return AgentCardResponse(
                code=0,
                message="success",
                data={"name": agent_name},
            )
        else:
            return AgentCardResponse(
                code=1,
                message="Failed to delete AgentCard",
            )

    except Exception as e:
        app_logger.error(f"删除 AgentCard 异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-cards/{agent_name}/versions", response_model=AgentCardResponse)
async def get_version_list(agent_name: str) -> AgentCardResponse:
    """
    获取 AgentCard 版本列表

    Args:
        agent_name: AgentCard 名称

    Returns:
        AgentCardResponse: 版本列表
    """
    try:
        manager = get_agent_card_manager()
        data = manager.get_version_list(agent_name=agent_name)

        if data is not None:
            return AgentCardResponse(
                code=0,
                message="success",
                data={"versions": data},
            )
        else:
            return AgentCardResponse(
                code=1,
                message="Failed to get version list",
            )

    except Exception as e:
        app_logger.error(f"获取版本列表异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

