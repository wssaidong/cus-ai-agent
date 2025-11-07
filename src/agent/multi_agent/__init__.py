"""
多智能体系统模块 - Supervisor 模式

提供基于 Supervisor 模式的多智能体协作功能

核心组件：
- SupervisorAgent: 监督者，负责任务分析和调度
- SearchAgent: 搜索智能体，负责知识库搜索
- WriteAgent: 写入智能体，负责知识库写入
- AnalysisAgent: 分析智能体，负责数据分析和推理
- ChatState: 聊天状态管理
- get_chat_graph: 获取聊天图实例
"""
from .agents import (
    SupervisorAgent,
    SearchAgent,
    WriteAgent,
    AnalysisAgent,
)
from .chat_state import ChatState, create_chat_state
from .chat_graph import get_chat_graph

__all__ = [
    # Supervisor 模式
    "SupervisorAgent",
    "SearchAgent",
    "WriteAgent",
    "AnalysisAgent",
    # 状态和图
    "ChatState",
    "create_chat_state",
    "get_chat_graph",
]

