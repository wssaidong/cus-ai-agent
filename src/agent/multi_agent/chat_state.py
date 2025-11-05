"""
多智能体系统 - 聊天状态定义

简化的状态结构，用于 Planner 和 Executor 之间的协作
"""
from typing import TypedDict, List, Annotated, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ChatState(TypedDict):
    """
    聊天状态
    
    Planner 和 Executor 通过此状态进行信息共享和协作
    所有历史消息保存在 messages 字段中，实现记忆功能
    """
    
    # 消息历史 - 使用 add_messages reducer 自动管理
    # 包含所有用户消息、智能体响应，实现记忆功能
    messages: Annotated[List[BaseMessage], add_messages]
    
    # 会话ID - 用于记忆隔离
    session_id: Optional[str]
    
    # 下一步行动 - 由 Planner 决定
    # 可选值: "execute" (调用执行者), "respond" (直接回答), "finish" (结束)
    next_action: Optional[str]
    
    # 执行指令 - Planner 给 Executor 的指令
    execution_instruction: Optional[str]
    
    # 是否完成
    is_finished: bool


def create_chat_state(
    messages: List[BaseMessage],
    session_id: Optional[str] = None,
) -> ChatState:
    """
    创建聊天状态
    
    Args:
        messages: 初始消息列表
        session_id: 会话ID
    
    Returns:
        ChatState: 初始化的聊天状态
    """
    return ChatState(
        messages=messages,
        session_id=session_id,
        next_action=None,
        execution_instruction=None,
        is_finished=False,
    )

