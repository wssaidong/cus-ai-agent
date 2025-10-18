"""
记忆功能测试
"""
import pytest
from src.agent.memory import MemoryManager, get_memory_manager, get_memory_saver
from langgraph.checkpoint.memory import MemorySaver


class TestMemoryManager:
    """记忆管理器测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.manager = MemoryManager()
    
    def test_memory_manager_initialization(self):
        """测试记忆管理器初始化"""
        assert self.manager is not None
        assert isinstance(self.manager.saver, MemorySaver)
        assert len(self.manager.sessions) == 0
    
    def test_create_session(self):
        """测试创建会话"""
        session_id = "test_session_1"
        session = self.manager.create_session(session_id)
        
        assert session["session_id"] == session_id
        assert session["message_count"] == 0
        assert session["created_at"] is not None
        assert session_id in self.manager.sessions
    
    def test_create_session_with_metadata(self):
        """测试创建带元数据的会话"""
        session_id = "test_session_2"
        metadata = {"user_id": "user123", "source": "api"}
        session = self.manager.create_session(session_id, metadata)
        
        assert session["metadata"] == metadata
        assert session["session_id"] == session_id
    
    def test_get_session(self):
        """测试获取会话"""
        session_id = "test_session_3"
        self.manager.create_session(session_id)
        
        session = self.manager.get_session(session_id)
        assert session is not None
        assert session["session_id"] == session_id
    
    def test_get_nonexistent_session(self):
        """测试获取不存在的会话"""
        session = self.manager.get_session("nonexistent")
        assert session is None
    
    def test_list_sessions(self):
        """测试列出所有会话"""
        self.manager.create_session("session_1")
        self.manager.create_session("session_2")
        self.manager.create_session("session_3")
        
        sessions = self.manager.list_sessions()
        assert len(sessions) == 3
    
    def test_record_checkpoint(self):
        """测试记录检查点"""
        session_id = "test_session_4"
        self.manager.create_session(session_id)
        
        state = {
            "messages": ["msg1", "msg2"],
            "metadata": {"key": "value"}
        }
        
        self.manager.record_checkpoint(session_id, "checkpoint_1", state)
        
        session = self.manager.get_session(session_id)
        assert len(session["checkpoints"]) == 1
        assert session["checkpoints"][0]["checkpoint_id"] == "checkpoint_1"
        assert session["message_count"] == 2
    
    def test_get_session_memory(self):
        """测试获取会话记忆"""
        session_id = "test_session_5"
        self.manager.create_session(session_id)
        
        state = {"messages": ["msg1"]}
        self.manager.record_checkpoint(session_id, "cp1", state)
        
        memory = self.manager.get_session_memory(session_id)
        assert memory["session_id"] == session_id
        assert memory["message_count"] == 1
        assert memory["checkpoint_count"] == 1
    
    def test_get_nonexistent_session_memory(self):
        """测试获取不存在会话的记忆"""
        memory = self.manager.get_session_memory("nonexistent")
        assert "error" in memory
    
    def test_clear_session_memory(self):
        """测试清空会话记忆"""
        session_id = "test_session_6"
        self.manager.create_session(session_id)
        
        success = self.manager.clear_session_memory(session_id)
        assert success is True
        assert self.manager.get_session(session_id) is None
    
    def test_clear_nonexistent_session_memory(self):
        """测试清空不存在的会话记忆"""
        success = self.manager.clear_session_memory("nonexistent")
        assert success is False
    
    def test_clear_all_memory(self):
        """测试清空所有记忆"""
        self.manager.create_session("session_1")
        self.manager.create_session("session_2")
        self.manager.create_session("session_3")
        
        count = self.manager.clear_all_memory()
        assert count == 3
        assert len(self.manager.sessions) == 0
    
    def test_get_memory_stats(self):
        """测试获取记忆统计"""
        self.manager.create_session("session_1")
        self.manager.create_session("session_2")
        
        state1 = {"messages": ["msg1", "msg2"]}
        state2 = {"messages": ["msg1"]}
        
        self.manager.record_checkpoint("session_1", "cp1", state1)
        self.manager.record_checkpoint("session_2", "cp1", state2)
        self.manager.record_checkpoint("session_2", "cp2", state2)
        
        stats = self.manager.get_memory_stats()
        assert stats["total_sessions"] == 2
        assert stats["total_messages"] == 3
        assert stats["total_checkpoints"] == 3
    
    def test_export_session_memory(self):
        """测试导出会话记忆"""
        session_id = "test_session_7"
        metadata = {"user_id": "user123"}
        self.manager.create_session(session_id, metadata)
        
        state = {"messages": ["msg1"]}
        self.manager.record_checkpoint(session_id, "cp1", state)
        
        exported = self.manager.export_session_memory(session_id)
        assert exported["session_id"] == session_id
        assert exported["metadata"] == metadata
        assert len(exported["checkpoints"]) == 1
    
    def test_export_nonexistent_session_memory(self):
        """测试导出不存在的会话记忆"""
        exported = self.manager.export_session_memory("nonexistent")
        assert "error" in exported


class TestMemoryGlobals:
    """全局记忆函数测试"""
    
    def test_get_memory_manager(self):
        """测试获取全局记忆管理器"""
        manager = get_memory_manager()
        assert manager is not None
        assert isinstance(manager, MemoryManager)
    
    def test_get_memory_saver(self):
        """测试获取 InMemorySaver"""
        saver = get_memory_saver()
        assert saver is not None
        assert isinstance(saver, MemorySaver)
    
    def test_memory_manager_singleton(self):
        """测试记忆管理器单例"""
        manager1 = get_memory_manager()
        manager2 = get_memory_manager()
        assert manager1 is manager2


class TestMemoryIntegration:
    """记忆集成测试"""
    
    def test_multiple_sessions_isolation(self):
        """测试多会话隔离"""
        manager = MemoryManager()
        
        manager.create_session("session_1")
        manager.create_session("session_2")
        
        state1 = {"messages": ["msg1"]}
        state2 = {"messages": ["msg2", "msg3"]}
        
        manager.record_checkpoint("session_1", "cp1", state1)
        manager.record_checkpoint("session_2", "cp1", state2)
        
        memory1 = manager.get_session_memory("session_1")
        memory2 = manager.get_session_memory("session_2")
        
        assert memory1["message_count"] == 1
        assert memory2["message_count"] == 2
    
    def test_checkpoint_history(self):
        """测试检查点历史"""
        manager = MemoryManager()
        session_id = "test_session"
        manager.create_session(session_id)
        
        # 记录多个检查点
        for i in range(5):
            state = {"messages": [f"msg{j}" for j in range(i + 1)]}
            manager.record_checkpoint(session_id, f"cp{i}", state)
        
        memory = manager.get_session_memory(session_id)
        assert memory["checkpoint_count"] == 5
        assert memory["message_count"] == 5

