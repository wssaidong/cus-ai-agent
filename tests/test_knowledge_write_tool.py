"""
知识库写入工具测试
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from src.tools.knowledge_write_tool import KnowledgeBaseWriteTool, KnowledgeBaseUpdateTool


class TestKnowledgeBaseWriteTool:
    """知识库写入工具测试"""

    @pytest.fixture
    def tool(self):
        """创建工具实例"""
        return KnowledgeBaseWriteTool()

    @pytest.fixture
    def mock_kb(self):
        """创建模拟知识库"""
        kb = Mock()
        kb.add_texts = Mock(return_value=["doc_id_123"])
        return kb

    def test_tool_name_and_description(self, tool):
        """测试工具名称和描述"""
        assert tool.name == "knowledge_base_write"
        assert "经验" in tool.description
        assert "知识库" in tool.description

    @patch('src.tools.knowledge_write_tool.get_knowledge_base')
    def test_write_experience_success(self, mock_get_kb, tool, mock_kb):
        """测试成功写入经验"""
        mock_get_kb.return_value = mock_kb
        
        # 准备输入
        input_data = {
            "content": "这是一个测试经验",
            "title": "测试标题",
            "category": "solution",
            "tags": "测试,经验",
            "source": "agent_experience"
        }
        
        # 执行
        result = tool._run(json.dumps(input_data))
        
        # 验证
        assert "成功" in result
        assert "doc_id_123" in result
        assert "测试标题" in result
        mock_kb.add_texts.assert_called_once()

    @patch('src.tools.knowledge_write_tool.get_knowledge_base')
    def test_write_experience_minimal_input(self, mock_get_kb, tool, mock_kb):
        """测试最小输入写入经验"""
        mock_get_kb.return_value = mock_kb
        
        # 只提供必需字段
        input_data = {
            "content": "最小化输入测试"
        }
        
        # 执行
        result = tool._run(json.dumps(input_data))
        
        # 验证
        assert "成功" in result
        mock_kb.add_texts.assert_called_once()

    def test_write_experience_missing_content(self, tool):
        """测试缺少内容字段"""
        input_data = {
            "title": "没有内容"
        }
        
        result = tool._run(json.dumps(input_data))
        
        assert "错误" in result
        assert "content" in result

    def test_write_experience_invalid_json(self, tool):
        """测试无效的JSON输入"""
        result = tool._run("invalid json {")
        
        assert "错误" in result
        assert "JSON" in result

    @patch('src.tools.knowledge_write_tool.get_knowledge_base')
    def test_write_experience_kb_error(self, mock_get_kb, tool):
        """测试知识库错误处理"""
        mock_kb = Mock()
        mock_kb.add_texts = Mock(side_effect=Exception("数据库连接失败"))
        mock_get_kb.return_value = mock_kb
        
        input_data = {
            "content": "测试内容"
        }
        
        result = tool._run(json.dumps(input_data))
        
        assert "失败" in result
        assert "数据库连接失败" in result

    @patch('src.tools.knowledge_write_tool.get_knowledge_base')
    def test_write_experience_no_document_id(self, mock_get_kb, tool):
        """测试未返回文档ID的情况"""
        mock_kb = Mock()
        mock_kb.add_texts = Mock(return_value=[])
        mock_get_kb.return_value = mock_kb
        
        input_data = {
            "content": "测试内容"
        }
        
        result = tool._run(json.dumps(input_data))
        
        assert "错误" in result
        assert "文档ID" in result

    @pytest.mark.asyncio
    @patch('src.tools.knowledge_write_tool.get_knowledge_base')
    async def test_write_experience_async(self, mock_get_kb, tool, mock_kb):
        """测试异步写入经验"""
        mock_get_kb.return_value = mock_kb
        
        input_data = {
            "content": "异步测试内容",
            "title": "异步测试"
        }
        
        result = await tool._arun(json.dumps(input_data))
        
        assert "成功" in result


class TestKnowledgeBaseUpdateTool:
    """知识库更新工具测试"""

    @pytest.fixture
    def tool(self):
        """创建工具实例"""
        return KnowledgeBaseUpdateTool()

    @pytest.fixture
    def mock_kb(self):
        """创建模拟知识库"""
        kb = Mock()
        kb.add_texts = Mock(return_value=["doc_id_456"])
        return kb

    def test_tool_name_and_description(self, tool):
        """测试工具名称和描述"""
        assert tool.name == "knowledge_base_update"
        assert "更新" in tool.description
        assert "知识库" in tool.description

    @patch('src.tools.knowledge_write_tool.get_knowledge_base')
    def test_update_experience_success(self, mock_get_kb, tool, mock_kb):
        """测试成功更新经验"""
        mock_get_kb.return_value = mock_kb
        
        input_data = {
            "content": "更新后的内容",
            "title": "更新标题",
            "category": "best_practice",
            "reason": "修正错误"
        }
        
        result = tool._run(json.dumps(input_data))
        
        assert "成功" in result
        assert "doc_id_456" in result
        assert "修正错误" in result
        mock_kb.add_texts.assert_called_once()

    @patch('src.tools.knowledge_write_tool.get_knowledge_base')
    def test_update_experience_minimal_input(self, mock_get_kb, tool, mock_kb):
        """测试最小输入更新经验"""
        mock_get_kb.return_value = mock_kb
        
        input_data = {
            "content": "最小化更新"
        }
        
        result = tool._run(json.dumps(input_data))
        
        assert "成功" in result
        mock_kb.add_texts.assert_called_once()

    def test_update_experience_missing_content(self, tool):
        """测试缺少内容字段"""
        input_data = {
            "title": "没有内容"
        }
        
        result = tool._run(json.dumps(input_data))
        
        assert "错误" in result
        assert "content" in result

    def test_update_experience_invalid_json(self, tool):
        """测试无效的JSON输入"""
        result = tool._run("invalid json {")
        
        assert "错误" in result
        assert "JSON" in result

    @patch('src.tools.knowledge_write_tool.get_knowledge_base')
    def test_update_experience_kb_error(self, mock_get_kb, tool):
        """测试知识库错误处理"""
        mock_kb = Mock()
        mock_kb.add_texts = Mock(side_effect=Exception("更新失败"))
        mock_get_kb.return_value = mock_kb
        
        input_data = {
            "content": "测试内容"
        }
        
        result = tool._run(json.dumps(input_data))
        
        assert "失败" in result
        assert "更新失败" in result

    @pytest.mark.asyncio
    @patch('src.tools.knowledge_write_tool.get_knowledge_base')
    async def test_update_experience_async(self, mock_get_kb, tool, mock_kb):
        """测试异步更新经验"""
        mock_get_kb.return_value = mock_kb
        
        input_data = {
            "content": "异步更新内容",
            "title": "异步更新"
        }
        
        result = await tool._arun(json.dumps(input_data))
        
        assert "成功" in result


class TestKnowledgeWriteToolIntegration:
    """集成测试"""

    def test_write_and_update_workflow(self):
        """测试写入和更新的工作流"""
        write_tool = KnowledgeBaseWriteTool()
        update_tool = KnowledgeBaseUpdateTool()
        
        # 验证两个工具都存在
        assert write_tool.name == "knowledge_base_write"
        assert update_tool.name == "knowledge_base_update"
        
        # 验证工具描述
        assert "经验" in write_tool.description
        assert "更新" in update_tool.description

