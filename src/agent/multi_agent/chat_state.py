"""
多智能体系统 - 聊天状态定义

支持 Supervisor 模式的状态结构，用于 Supervisor 和 Worker Agents 之间的协作
"""
from typing import TypedDict, List, Annotated, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ChatState(TypedDict):
    """
    聊天状态 - Supervisor 模式

    Supervisor 和 Worker Agents 通过此状态进行信息共享和协作
    所有历史消息保存在 messages 字段中，实现记忆功能

    状态流转：
    1. 用户输入 -> Supervisor 分析
    2. Supervisor 决定 next_agent 和 task_instruction
    3. Worker Agent 执行任务，更新 messages
    4. 返回 Supervisor 或结束
    """

    # 消息历史 - 使用 add_messages reducer 自动管理
    # 包含所有用户消息、智能体响应，实现记忆功能
    messages: Annotated[List[BaseMessage], add_messages]

    # 会话ID - 用于记忆隔离
    session_id: Optional[str]

    # 下一个 Agent - 由 Supervisor 决定
    # 可选值:
    #   - "search_agent" (搜索智能体)
    #   - "write_agent" (写入智能体)
    #   - "analysis_agent" (分析智能体)
    #   - "respond" (直接回答)
    #   - "finish" (结束)
    next_agent: Optional[str]

    # 任务指令 - Supervisor 给 Worker Agent 的任务指令
    task_instruction: Optional[str]

    # 是否完成
    is_finished: bool


def create_chat_state(
    messages: List[BaseMessage],
    session_id: Optional[str] = None,
) -> ChatState:
    """
    创建聊天状态 - Supervisor 模式

    Args:
        messages: 初始消息列表
        session_id: 会话ID

    Returns:
        ChatState: 初始化的聊天状态
    """
    return ChatState(
        messages=messages,
        session_id=session_id,
        next_agent=None,
        task_instruction=None,
        is_finished=False,
    )

