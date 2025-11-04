"""
多智能体系统 API 路由

提供多智能体协作的 REST API 接口
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.agent.multi_agent.multi_agent_state import create_initial_state
from src.agent.multi_agent.multi_agent_graph import multi_agent_graph
from src.agent.multi_agent.agent_registry import agent_registry
from src.agent.multi_agent.agent_coordinator import agent_coordinator
from src.utils import app_logger


# 创建路由
router = APIRouter(prefix="/api/v1/multi-agent", tags=["多智能体系统"])


# 请求/响应模型

class MultiAgentTaskRequest(BaseModel):
    """多智能体任务请求"""
    description: str = Field(..., description="任务描述")
    type: Optional[str] = Field(None, description="任务类型")
    context: Optional[str] = Field(None, description="上下文信息")
    requirements: Optional[List[str]] = Field(default_factory=list, description="需求列表")
    coordination_mode: str = Field(default="sequential", description="协作模式: sequential/parallel/hierarchical/feedback")
    session_id: Optional[str] = Field(None, description="会话ID")
    max_iterations: int = Field(default=10, description="最大迭代次数")
    max_feedback_rounds: int = Field(default=3, description="最大反馈轮次")


class MultiAgentTaskResponse(BaseModel):
    """多智能体任务响应"""
    code: int = Field(..., description="状态码")
    message: str = Field(..., description="消息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")


class AgentInfo(BaseModel):
    """智能体信息"""
    agent_id: str
    agent_type: str
    name: str
    description: str
    status: str
    capabilities: List[Dict[str, Any]]


class AgentListResponse(BaseModel):
    """智能体列表响应"""
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


# API 端点

@router.post("/tasks", response_model=MultiAgentTaskResponse)
async def execute_multi_agent_task(request: MultiAgentTaskRequest) -> MultiAgentTaskResponse:
    """
    执行多智能体任务
    
    Args:
        request: 任务请求
        
    Returns:
        MultiAgentTaskResponse: 执行结果
    """
    try:
        app_logger.info(f"接收多智能体任务: {request.description}")
        
        # 构建任务
        task = {
            "description": request.description,
            "type": request.type,
            "context": request.context,
            "requirements": request.requirements,
        }
        
        # 创建初始状态
        initial_state = create_initial_state(
            task=task,
            session_id=request.session_id,
            coordination_mode=request.coordination_mode,
            max_iterations=request.max_iterations,
            max_feedback_rounds=request.max_feedback_rounds,
        )
        
        # 执行多智能体协作
        config = {}
        if request.session_id:
            config["configurable"] = {"thread_id": request.session_id}
        
        result = await multi_agent_graph.ainvoke(initial_state, config=config)
        
        # 提取最终结果
        final_result = result.get("final_result", {})
        
        return MultiAgentTaskResponse(
            code=0,
            message="success",
            data={
                "task": task,
                "coordination_mode": request.coordination_mode,
                "agents_involved": list(result.get("agent_results", {}).keys()),
                "final_result": final_result,
                "is_finished": result.get("is_finished", False),
                "error": result.get("error"),
            }
        )
        
    except Exception as e:
        app_logger.error(f"执行多智能体任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents", response_model=AgentListResponse)
async def list_agents() -> AgentListResponse:
    """
    获取所有智能体列表
    
    Returns:
        AgentListResponse: 智能体列表
    """
    try:
        agents = agent_registry.get_all_agents()
        
        agent_list = []
        for agent in agents:
            metadata = agent.get_metadata()
            agent_list.append({
                "agent_id": metadata.agent_id,
                "agent_type": metadata.agent_type.value,
                "name": metadata.name,
                "description": metadata.description,
                "status": metadata.status.value,
                "capabilities": [
                    {
                        "name": cap.name,
                        "description": cap.description,
                        "confidence": cap.confidence
                    }
                    for cap in metadata.capabilities
                ]
            })
        
        return AgentListResponse(
            code=0,
            message="success",
            data={
                "agents": agent_list,
                "total": len(agent_list)
            }
        )
        
    except Exception as e:
        app_logger.error(f"获取智能体列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}", response_model=AgentListResponse)
async def get_agent(agent_id: str) -> AgentListResponse:
    """
    获取指定智能体信息
    
    Args:
        agent_id: 智能体ID
        
    Returns:
        AgentListResponse: 智能体信息
    """
    try:
        agent = agent_registry.get_agent(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"智能体 {agent_id} 不存在")
        
        metadata = agent.get_metadata()
        
        return AgentListResponse(
            code=0,
            message="success",
            data={
                "agent_id": metadata.agent_id,
                "agent_type": metadata.agent_type.value,
                "name": metadata.name,
                "description": metadata.description,
                "status": metadata.status.value,
                "version": metadata.version,
                "capabilities": [
                    {
                        "name": cap.name,
                        "description": cap.description,
                        "confidence": cap.confidence,
                        "required_tools": cap.required_tools
                    }
                    for cap in metadata.capabilities
                ],
                "execution_history": agent.get_execution_history()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"获取智能体信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=AgentListResponse)
async def get_statistics() -> AgentListResponse:
    """
    获取多智能体系统统计信息
    
    Returns:
        AgentListResponse: 统计信息
    """
    try:
        stats = agent_registry.get_statistics()
        
        return AgentListResponse(
            code=0,
            message="success",
            data=stats
        )
        
    except Exception as e:
        app_logger.error(f"获取统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/sequential", response_model=MultiAgentTaskResponse)
async def test_sequential_mode() -> MultiAgentTaskResponse:
    """
    测试顺序协作模式
    
    Returns:
        MultiAgentTaskResponse: 测试结果
    """
    request = MultiAgentTaskRequest(
        description="分析并制定一个简单的项目计划",
        type="planning",
        context="新项目启动",
        requirements=["需求分析", "任务分解", "时间估算"],
        coordination_mode="sequential"
    )
    
    return await execute_multi_agent_task(request)


@router.post("/test/feedback", response_model=MultiAgentTaskResponse)
async def test_feedback_mode() -> MultiAgentTaskResponse:
    """
    测试反馈协作模式
    
    Returns:
        MultiAgentTaskResponse: 测试结果
    """
    request = MultiAgentTaskRequest(
        description="生成一个高质量的产品介绍文案",
        type="content_generation",
        requirements=["吸引人", "专业", "简洁"],
        coordination_mode="feedback",
        max_feedback_rounds=2
    )
    
    return await execute_multi_agent_task(request)

