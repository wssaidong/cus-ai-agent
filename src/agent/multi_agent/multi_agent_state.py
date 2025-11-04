"""
多智能体系统 - 共享状态定义

定义多智能体系统的共享状态结构
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class MultiAgentState(TypedDict):
    """
    多智能体系统共享状态
    
    所有智能体通过此状态进行信息共享和协作
    """
    
    # ========== 基础字段 ==========
    
    # 消息历史 - 使用 add_messages reducer
    messages: Annotated[List[BaseMessage], add_messages]
    
    # 会话ID
    session_id: Optional[str]
    
    # ========== 任务相关 ==========
    
    # 原始任务
    task: Dict[str, Any]
    
    # 任务类型
    task_type: Optional[str]
    
    # 任务计划 - 由 PlannerAgent 生成
    task_plan: List[Dict[str, Any]]
    
    # 当前执行的子任务
    current_subtask: Optional[Dict[str, Any]]
    
    # 子任务索引
    subtask_index: int
    
    # ========== 智能体相关 ==========
    
    # 当前执行的智能体ID
    current_agent: Optional[str]
    
    # 各智能体的执行结果
    agent_results: Dict[str, Any]
    
    # 智能体执行历史
    agent_history: List[Dict[str, Any]]
    
    # 下一个要执行的智能体
    next_agent: Optional[str]
    
    # ========== 协作相关 ==========
    
    # 协作模式: sequential/parallel/hierarchical/feedback
    coordination_mode: str
    
    # 是否需要反馈循环
    needs_feedback: bool
    
    # 反馈轮次
    feedback_round: int
    
    # 最大反馈轮次
    max_feedback_rounds: int
    
    # ========== 结果相关 ==========
    
    # 中间结果列表
    intermediate_results: List[Dict[str, Any]]
    
    # 最终结果
    final_result: Optional[Dict[str, Any]]
    
    # 是否完成
    is_finished: bool
    
    # ========== 质量控制 ==========
    
    # 评审结果
    review_result: Optional[Dict[str, Any]]
    
    # 是否通过评审
    review_passed: bool
    
    # 改进建议
    improvement_suggestions: List[str]
    
    # ========== 元数据 ==========
    
    # 元数据
    metadata: Dict[str, Any]
    
    # 迭代次数
    iteration: int
    
    # 最大迭代次数
    max_iterations: int
    
    # 开始时间
    start_time: Optional[str]
    
    # 结束时间
    end_time: Optional[str]
    
    # 错误信息
    error: Optional[str]


def create_initial_state(
    task: Dict[str, Any],
    session_id: Optional[str] = None,
    coordination_mode: str = "sequential",
    max_iterations: int = 10,
    max_feedback_rounds: int = 3,
) -> MultiAgentState:
    """
    创建初始状态
    
    Args:
        task: 任务描述
        session_id: 会话ID
        coordination_mode: 协作模式
        max_iterations: 最大迭代次数
        max_feedback_rounds: 最大反馈轮次
        
    Returns:
        MultiAgentState: 初始化的状态
    """
    from datetime import datetime
    
    return MultiAgentState(
        # 基础字段
        messages=[],
        session_id=session_id,
        
        # 任务相关
        task=task,
        task_type=task.get("type"),
        task_plan=[],
        current_subtask=None,
        subtask_index=0,
        
        # 智能体相关
        current_agent=None,
        agent_results={},
        agent_history=[],
        next_agent=None,
        
        # 协作相关
        coordination_mode=coordination_mode,
        needs_feedback=False,
        feedback_round=0,
        max_feedback_rounds=max_feedback_rounds,
        
        # 结果相关
        intermediate_results=[],
        final_result=None,
        is_finished=False,
        
        # 质量控制
        review_result=None,
        review_passed=False,
        improvement_suggestions=[],
        
        # 元数据
        metadata={
            "created_at": datetime.now().isoformat(),
        },
        iteration=0,
        max_iterations=max_iterations,
        start_time=datetime.now().isoformat(),
        end_time=None,
        error=None,
    )


def update_agent_result(
    state: MultiAgentState,
    agent_id: str,
    result: Dict[str, Any]
) -> MultiAgentState:
    """
    更新智能体执行结果
    
    Args:
        state: 当前状态
        agent_id: 智能体ID
        result: 执行结果
        
    Returns:
        MultiAgentState: 更新后的状态
    """
    # 更新结果
    state["agent_results"][agent_id] = result
    
    # 添加到历史
    state["agent_history"].append({
        "agent_id": agent_id,
        "result": result,
        "timestamp": _get_timestamp(),
    })
    
    # 添加到中间结果
    state["intermediate_results"].append(result)
    
    return state


def mark_finished(
    state: MultiAgentState,
    final_result: Dict[str, Any]
) -> MultiAgentState:
    """
    标记任务完成
    
    Args:
        state: 当前状态
        final_result: 最终结果
        
    Returns:
        MultiAgentState: 更新后的状态
    """
    from datetime import datetime
    
    state["is_finished"] = True
    state["final_result"] = final_result
    state["end_time"] = datetime.now().isoformat()
    
    return state


def mark_error(
    state: MultiAgentState,
    error: str
) -> MultiAgentState:
    """
    标记错误
    
    Args:
        state: 当前状态
        error: 错误信息
        
    Returns:
        MultiAgentState: 更新后的状态
    """
    from datetime import datetime
    
    state["is_finished"] = True
    state["error"] = error
    state["end_time"] = datetime.now().isoformat()
    
    return state


def _get_timestamp() -> str:
    """获取当前时间戳"""
    from datetime import datetime
    return datetime.now().isoformat()

