"""
智能体状态定义
"""
from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """智能体状态"""

    # 消息历史
    messages: List[BaseMessage]

    # 中间步骤
    intermediate_steps: List[tuple]

    # 工具调用结果
    tool_results: List[Dict[str, Any]]

    # 最终响应
    final_response: Optional[str]

    # 元数据
    metadata: Dict[str, Any]

    # 迭代次数
    iteration: int

    # 是否完成
    is_finished: bool

    # 记忆相关字段
    session_id: Optional[str]  # 会话ID，用于记忆隔离
    memory_enabled: bool  # 是否启用记忆功能

