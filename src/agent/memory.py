"""
记忆管理模块 - 使用 InMemorySaver 实现对话记忆

此模块提供：
1. InMemorySaver - 内存中的状态保存器
2. MemoryManager - 记忆管理器，用于查询、清空、导出记忆
3. 会话级别的记忆隔离
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from langgraph.checkpoint.memory import MemorySaver
from src.utils import app_logger


class MemoryManager:
    """
    记忆管理器 - 管理对话记忆和会话状态
    
    特性：
    - 支持多会话隔离
    - 记忆持久化查询
    - 记忆统计和分析
    - 记忆清空和导出
    """
    
    def __init__(self):
        """初始化记忆管理器"""
        self.saver = MemorySaver()
        self.sessions: Dict[str, Dict[str, Any]] = {}
        app_logger.info("记忆管理器初始化完成")
    
    def create_session(self, session_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        创建新会话
        
        Args:
            session_id: 会话ID
            metadata: 会话元数据
            
        Returns:
            会话信息
        """
        if session_id in self.sessions:
            app_logger.warning(f"会话 {session_id} 已存在")
            return self.sessions[session_id]
        
        session_info = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "message_count": 0,
            "metadata": metadata or {},
            "checkpoints": []
        }
        
        self.sessions[session_id] = session_info
        app_logger.info(f"创建会话: {session_id}")
        return session_info
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        return self.sessions.get(session_id)
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话"""
        return list(self.sessions.values())
    
    def record_checkpoint(self, session_id: str, checkpoint_id: str, state: Dict[str, Any]) -> None:
        """
        记录检查点
        
        Args:
            session_id: 会话ID
            checkpoint_id: 检查点ID
            state: 状态数据
        """
        if session_id not in self.sessions:
            self.create_session(session_id)
        
        session = self.sessions[session_id]
        checkpoint_info = {
            "checkpoint_id": checkpoint_id,
            "timestamp": datetime.now().isoformat(),
            "state_keys": list(state.keys()) if isinstance(state, dict) else [],
            "message_count": len(state.get("messages", [])) if isinstance(state, dict) else 0
        }
        
        session["checkpoints"].append(checkpoint_info)
        session["updated_at"] = datetime.now().isoformat()
        session["message_count"] = checkpoint_info["message_count"]
        
        app_logger.debug(f"记录检查点: {session_id}/{checkpoint_id}")
    
    def get_session_memory(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话的记忆信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            记忆信息
        """
        session = self.get_session(session_id)
        if not session:
            return {"error": f"会话 {session_id} 不存在"}
        
        return {
            "session_id": session_id,
            "created_at": session["created_at"],
            "updated_at": session["updated_at"],
            "message_count": session["message_count"],
            "checkpoint_count": len(session["checkpoints"]),
            "checkpoints": session["checkpoints"][-10:],  # 返回最后10个检查点
            "metadata": session["metadata"]
        }
    
    def clear_session_memory(self, session_id: str) -> bool:
        """
        清空会话记忆
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功
        """
        if session_id not in self.sessions:
            app_logger.warning(f"会话 {session_id} 不存在")
            return False
        
        del self.sessions[session_id]
        app_logger.info(f"清空会话记忆: {session_id}")
        return True
    
    def clear_all_memory(self) -> int:
        """
        清空所有记忆
        
        Returns:
            清空的会话数
        """
        count = len(self.sessions)
        self.sessions.clear()
        app_logger.info(f"清空所有记忆，共 {count} 个会话")
        return count
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        获取记忆统计信息
        
        Returns:
            统计信息
        """
        total_sessions = len(self.sessions)
        total_messages = sum(s["message_count"] for s in self.sessions.values())
        total_checkpoints = sum(len(s["checkpoints"]) for s in self.sessions.values())
        
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "total_checkpoints": total_checkpoints,
            "average_messages_per_session": total_messages / total_sessions if total_sessions > 0 else 0,
            "average_checkpoints_per_session": total_checkpoints / total_sessions if total_sessions > 0 else 0
        }
    
    def export_session_memory(self, session_id: str) -> Dict[str, Any]:
        """
        导出会话记忆
        
        Args:
            session_id: 会话ID
            
        Returns:
            导出的记忆数据
        """
        session = self.get_session(session_id)
        if not session:
            return {"error": f"会话 {session_id} 不存在"}
        
        return {
            "session_id": session_id,
            "created_at": session["created_at"],
            "updated_at": session["updated_at"],
            "message_count": session["message_count"],
            "checkpoints": session["checkpoints"],
            "metadata": session["metadata"]
        }


# 全局记忆管理器实例
memory_manager = MemoryManager()


def get_memory_manager() -> MemoryManager:
    """获取全局记忆管理器实例"""
    return memory_manager


def get_memory_saver() -> MemorySaver:
    """获取 InMemorySaver 实例"""
    return memory_manager.saver

