"""
问法推荐功能测试
"""
import pytest
from src.agent.recommendation_engine import (
    QuestionRecommender, Recommendation, RecommendationType, ContextAnalysis
)
from src.agent.recommendation_feedback import (
    FeedbackManager, RecommendationFeedback, FeedbackType, UserAction
)
import tempfile
from pathlib import Path


class TestQuestionRecommender:
    """问法推荐引擎测试"""
    
    @pytest.fixture
    def recommender(self):
        """创建推荐引擎实例"""
        return QuestionRecommender()
    
    def test_recommender_initialization(self, recommender):
        """测试推荐引擎初始化"""
        assert recommender is not None
        assert recommender.llm is not None
        assert recommender.recommendation_counter == 0
    
    def test_analyze_context(self, recommender):
        """测试上下文分析"""
        current_message = "如何使用API"
        conversation_history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好，有什么我可以帮助的吗？"}
        ]
        
        context = recommender.analyze_context(current_message, conversation_history)
        
        assert isinstance(context, ContextAnalysis)
        assert context.conversation_depth == 2
        assert context.user_intent in ["inquiry", "help", "clarification", "exploration"]
    
    def test_analyze_context_empty_history(self, recommender):
        """测试空对话历史的上下文分析"""
        current_message = "你好"
        context = recommender.analyze_context(current_message, [])
        
        assert isinstance(context, ContextAnalysis)
        assert context.conversation_depth == 0
    
    def test_generate_recommendations(self, recommender):
        """测试推荐生成"""
        current_message = "如何使用API"
        conversation_history = []
        
        recommendations = recommender.generate_recommendations(
            current_message=current_message,
            conversation_history=conversation_history,
            num_recommendations=3
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) <= 3
        
        for rec in recommendations:
            assert isinstance(rec, Recommendation)
            assert rec.question
            assert rec.reason
            assert 0 <= rec.composite_score <= 1
            assert 0 <= rec.relevance_score <= 1
            assert 0 <= rec.answerability_score <= 1
    
    def test_recommendation_scoring(self, recommender):
        """测试推荐评分"""
        rec = Recommendation(
            id="test-1",
            question="测试问题",
            reason="测试理由",
            recommendation_type=RecommendationType.FOLLOW_UP,
            relevance_score=0.8,
            answerability_score=0.7,
            user_interest_score=0.6
        )
        
        # 验证综合评分计算
        expected_score = 0.4 * 0.8 + 0.3 * 0.7 + 0.3 * 0.6
        assert abs(rec.composite_score - expected_score) < 0.001
    
    def test_recommendation_to_dict(self, recommender):
        """测试推荐转换为字典"""
        rec = Recommendation(
            id="test-1",
            question="测试问题",
            reason="测试理由",
            recommendation_type=RecommendationType.FOLLOW_UP,
            relevance_score=0.8,
            answerability_score=0.7,
            confidence=0.75
        )
        
        rec_dict = rec.to_dict()
        
        assert rec_dict["id"] == "test-1"
        assert rec_dict["question"] == "测试问题"
        assert rec_dict["type"] == "follow_up"
        assert "score" in rec_dict
        assert "relevance_score" in rec_dict
    
    def test_calculate_relevance_score(self, recommender):
        """测试相关性评分计算"""
        context = ContextAnalysis(
            main_topic="API",
            user_intent="inquiry",
            keywords=["API", "参数", "调用"],
            entities=["OpenAI"]
        )
        
        # 包含关键词的问题应该有更高的分数
        score1 = recommender._calculate_relevance_score("API有哪些参数？", context)
        score2 = recommender._calculate_relevance_score("天气怎么样？", context)
        
        assert score1 > score2
    
    def test_calculate_answerability_score(self, recommender):
        """测试可解答性评分计算"""
        # 具体问题应该有更高的分数
        score1 = recommender._calculate_answerability_score("如何使用API调用？")
        score2 = recommender._calculate_answerability_score("嗯")
        
        assert score1 > score2


class TestFeedbackManager:
    """反馈管理器测试"""
    
    @pytest.fixture
    def temp_storage(self):
        """创建临时存储路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "feedback.jsonl"
    
    @pytest.fixture
    def feedback_manager(self, temp_storage):
        """创建反馈管理器实例"""
        return FeedbackManager(storage_path=str(temp_storage))
    
    def test_feedback_manager_initialization(self, feedback_manager):
        """测试反馈管理器初始化"""
        assert feedback_manager is not None
        assert feedback_manager.storage_path is not None
        assert isinstance(feedback_manager.feedback_cache, list)
    
    def test_submit_feedback(self, feedback_manager):
        """测试提交反馈"""
        success = feedback_manager.submit_feedback(
            recommendation_id="rec-001",
            session_id="user-123",
            feedback_type="helpful",
            user_action="clicked",
            user_comment="很有帮助"
        )
        
        assert success is True
        assert len(feedback_manager.feedback_cache) == 1
    
    def test_submit_invalid_feedback_type(self, feedback_manager):
        """测试提交无效的反馈类型"""
        success = feedback_manager.submit_feedback(
            recommendation_id="rec-001",
            session_id="user-123",
            feedback_type="invalid_type",
            user_action="clicked"
        )
        
        assert success is False
    
    def test_submit_invalid_user_action(self, feedback_manager):
        """测试提交无效的用户行为"""
        success = feedback_manager.submit_feedback(
            recommendation_id="rec-001",
            session_id="user-123",
            feedback_type="helpful",
            user_action="invalid_action"
        )
        
        assert success is False
    
    def test_get_feedback_stats(self, feedback_manager):
        """测试获取反馈统计"""
        # 提交多个反馈
        feedback_manager.submit_feedback("rec-001", "user-123", "helpful", "clicked")
        feedback_manager.submit_feedback("rec-002", "user-123", "not_helpful", "ignored")
        feedback_manager.submit_feedback("rec-003", "user-456", "helpful", "clicked")
        
        stats = feedback_manager.get_feedback_stats()
        
        assert stats["total_feedback"] == 3
        assert stats["feedback_types"]["helpful"] == 2
        assert stats["feedback_types"]["not_helpful"] == 1
        assert stats["user_actions"]["clicked"] == 2
        assert stats["user_actions"]["ignored"] == 1
        assert stats["helpful_rate"] == pytest.approx(2/3, abs=0.01)
        assert stats["click_rate"] == pytest.approx(2/3, abs=0.01)
    
    def test_get_session_feedback(self, feedback_manager):
        """测试获取会话反馈"""
        feedback_manager.submit_feedback("rec-001", "user-123", "helpful", "clicked")
        feedback_manager.submit_feedback("rec-002", "user-123", "not_helpful", "ignored")
        feedback_manager.submit_feedback("rec-003", "user-456", "helpful", "clicked")
        
        session_feedback = feedback_manager.get_session_feedback("user-123")
        
        assert len(session_feedback) == 2
        assert all(f["session_id"] == "user-123" for f in session_feedback)
    
    def test_get_recommendation_feedback(self, feedback_manager):
        """测试获取推荐反馈"""
        feedback_manager.submit_feedback("rec-001", "user-123", "helpful", "clicked")
        feedback_manager.submit_feedback("rec-001", "user-456", "not_helpful", "ignored")
        feedback_manager.submit_feedback("rec-002", "user-123", "helpful", "clicked")
        
        rec_feedback = feedback_manager.get_recommendation_feedback("rec-001")
        
        assert len(rec_feedback) == 2
        assert all(f["recommendation_id"] == "rec-001" for f in rec_feedback)
    
    def test_analyze_feedback_trends(self, feedback_manager):
        """测试分析反馈趋势"""
        # 提交多个反馈
        for i in range(5):
            feedback_manager.submit_feedback(
                f"rec-{i:03d}",
                f"user-{i % 2}",
                "helpful" if i % 2 == 0 else "not_helpful",
                "clicked" if i % 3 == 0 else "ignored"
            )
        
        trends = feedback_manager.analyze_feedback_trends(limit=10)
        
        assert "analyzed_feedback_count" in trends
        assert "feedback_type_distribution" in trends
        assert "user_action_distribution" in trends
        assert "most_common_feedback" in trends
        assert "most_common_action" in trends
    
    def test_feedback_persistence(self, temp_storage):
        """测试反馈持久化"""
        # 创建第一个管理器并提交反馈
        manager1 = FeedbackManager(storage_path=str(temp_storage))
        manager1.submit_feedback("rec-001", "user-123", "helpful", "clicked")
        
        # 创建第二个管理器，应该加载之前的反馈
        manager2 = FeedbackManager(storage_path=str(temp_storage))
        
        assert len(manager2.feedback_cache) == 1
        assert manager2.feedback_cache[0].recommendation_id == "rec-001"


class TestRecommendationFeedback:
    """推荐反馈数据模型测试"""
    
    def test_feedback_creation(self):
        """测试反馈创建"""
        feedback = RecommendationFeedback(
            recommendation_id="rec-001",
            session_id="user-123",
            feedback_type=FeedbackType.HELPFUL,
            user_action=UserAction.CLICKED,
            user_comment="很有帮助"
        )
        
        assert feedback.recommendation_id == "rec-001"
        assert feedback.session_id == "user-123"
        assert feedback.feedback_type == FeedbackType.HELPFUL
        assert feedback.user_action == UserAction.CLICKED
    
    def test_feedback_to_dict(self):
        """测试反馈转换为字典"""
        feedback = RecommendationFeedback(
            recommendation_id="rec-001",
            session_id="user-123",
            feedback_type=FeedbackType.HELPFUL,
            user_action=UserAction.CLICKED
        )
        
        feedback_dict = feedback.to_dict()
        
        assert feedback_dict["recommendation_id"] == "rec-001"
        assert feedback_dict["feedback_type"] == "helpful"
        assert feedback_dict["user_action"] == "clicked"
        assert "timestamp" in feedback_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

