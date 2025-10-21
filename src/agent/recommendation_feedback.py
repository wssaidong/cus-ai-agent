"""
推荐反馈管理器
用于收集和分析用户对推荐的反馈，优化推荐模型
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
from src.utils import app_logger


class FeedbackType(Enum):
    """反馈类型"""
    HELPFUL = "helpful"               # 有帮助
    NOT_HELPFUL = "not_helpful"       # 没有帮助
    IRRELEVANT = "irrelevant"         # 不相关
    DUPLICATE = "duplicate"           # 重复


class UserAction(Enum):
    """用户行为"""
    CLICKED = "clicked"               # 点击了推荐
    IGNORED = "ignored"               # 忽略了推荐
    DISMISSED = "dismissed"           # 关闭了推荐


@dataclass
class RecommendationFeedback:
    """推荐反馈"""
    recommendation_id: str
    session_id: str
    feedback_type: FeedbackType
    user_action: UserAction
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    user_comment: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "recommendation_id": self.recommendation_id,
            "session_id": self.session_id,
            "feedback_type": self.feedback_type.value,
            "user_action": self.user_action.value,
            "timestamp": self.timestamp,
            "user_comment": self.user_comment,
            "metadata": self.metadata,
        }


class FeedbackManager:
    """推荐反馈管理器"""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化反馈管理器
        
        Args:
            storage_path: 反馈存储路径，默认为 ./data/recommendation_feedback.jsonl
        """
        self.storage_path = Path(storage_path or "./data/recommendation_feedback.jsonl")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.feedback_cache: List[RecommendationFeedback] = []
        self._load_feedback()
    
    def submit_feedback(self,
                       recommendation_id: str,
                       session_id: str,
                       feedback_type: str,
                       user_action: str,
                       user_comment: Optional[str] = None,
                       metadata: Optional[Dict] = None) -> bool:
        """
        提交推荐反馈
        
        Args:
            recommendation_id: 推荐ID
            session_id: 会话ID
            feedback_type: 反馈类型 (helpful/not_helpful/irrelevant/duplicate)
            user_action: 用户行为 (clicked/ignored/dismissed)
            user_comment: 用户评论
            metadata: 额外元数据
            
        Returns:
            bool: 是否成功提交
        """
        try:
            feedback = RecommendationFeedback(
                recommendation_id=recommendation_id,
                session_id=session_id,
                feedback_type=FeedbackType(feedback_type),
                user_action=UserAction(user_action),
                user_comment=user_comment,
                metadata=metadata or {}
            )
            
            self.feedback_cache.append(feedback)
            self._save_feedback(feedback)
            
            app_logger.info(
                f"反馈已提交: {recommendation_id} - {feedback_type} - {user_action}"
            )
            
            return True
            
        except ValueError as e:
            app_logger.error(f"无效的反馈类型或用户行为: {str(e)}")
            return False
        except Exception as e:
            app_logger.error(f"提交反馈失败: {str(e)}")
            return False
    
    def get_feedback_stats(self) -> Dict:
        """
        获取反馈统计信息
        
        Returns:
            Dict: 统计信息
        """
        if not self.feedback_cache:
            return {
                "total_feedback": 0,
                "feedback_types": {},
                "user_actions": {},
                "helpful_rate": 0.0,
                "click_rate": 0.0,
            }
        
        total = len(self.feedback_cache)
        
        # 统计反馈类型
        feedback_types = {}
        for feedback in self.feedback_cache:
            ft = feedback.feedback_type.value
            feedback_types[ft] = feedback_types.get(ft, 0) + 1
        
        # 统计用户行为
        user_actions = {}
        for feedback in self.feedback_cache:
            ua = feedback.user_action.value
            user_actions[ua] = user_actions.get(ua, 0) + 1
        
        # 计算有帮助率
        helpful_count = feedback_types.get("helpful", 0)
        helpful_rate = helpful_count / total if total > 0 else 0.0
        
        # 计算点击率
        click_count = user_actions.get("clicked", 0)
        click_rate = click_count / total if total > 0 else 0.0
        
        return {
            "total_feedback": total,
            "feedback_types": feedback_types,
            "user_actions": user_actions,
            "helpful_rate": round(helpful_rate, 3),
            "click_rate": round(click_rate, 3),
            "average_feedback_per_session": round(total / len(set(f.session_id for f in self.feedback_cache)), 2),
        }
    
    def get_session_feedback(self, session_id: str) -> List[Dict]:
        """
        获取特定会话的反馈
        
        Args:
            session_id: 会话ID
            
        Returns:
            List[Dict]: 反馈列表
        """
        session_feedback = [
            f for f in self.feedback_cache
            if f.session_id == session_id
        ]
        return [f.to_dict() for f in session_feedback]
    
    def get_recommendation_feedback(self, recommendation_id: str) -> List[Dict]:
        """
        获取特定推荐的反馈
        
        Args:
            recommendation_id: 推荐ID
            
        Returns:
            List[Dict]: 反馈列表
        """
        rec_feedback = [
            f for f in self.feedback_cache
            if f.recommendation_id == recommendation_id
        ]
        return [f.to_dict() for f in rec_feedback]
    
    def analyze_feedback_trends(self, limit: int = 100) -> Dict:
        """
        分析反馈趋势
        
        Args:
            limit: 分析的最近反馈数量
            
        Returns:
            Dict: 趋势分析结果
        """
        recent_feedback = self.feedback_cache[-limit:]
        
        if not recent_feedback:
            return {"message": "没有反馈数据"}
        
        # 按反馈类型分组
        by_type = {}
        for feedback in recent_feedback:
            ft = feedback.feedback_type.value
            if ft not in by_type:
                by_type[ft] = []
            by_type[ft].append(feedback)
        
        # 计算每种类型的比例
        total = len(recent_feedback)
        type_distribution = {
            ft: round(len(feedbacks) / total, 3)
            for ft, feedbacks in by_type.items()
        }
        
        # 计算用户行为分布
        by_action = {}
        for feedback in recent_feedback:
            ua = feedback.user_action.value
            if ua not in by_action:
                by_action[ua] = 0
            by_action[ua] += 1
        
        action_distribution = {
            ua: round(count / total, 3)
            for ua, count in by_action.items()
        }
        
        return {
            "analyzed_feedback_count": total,
            "feedback_type_distribution": type_distribution,
            "user_action_distribution": action_distribution,
            "most_common_feedback": max(by_type.keys(), key=lambda k: len(by_type[k])),
            "most_common_action": max(by_action.keys(), key=lambda k: by_action[k]),
        }
    
    def _save_feedback(self, feedback: RecommendationFeedback) -> None:
        """保存反馈到文件"""
        try:
            with open(self.storage_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(feedback.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            app_logger.error(f"保存反馈失败: {str(e)}")
    
    def _load_feedback(self) -> None:
        """从文件加载反馈"""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            feedback = RecommendationFeedback(
                                recommendation_id=data["recommendation_id"],
                                session_id=data["session_id"],
                                feedback_type=FeedbackType(data["feedback_type"]),
                                user_action=UserAction(data["user_action"]),
                                timestamp=data.get("timestamp", datetime.now().isoformat()),
                                user_comment=data.get("user_comment"),
                                metadata=data.get("metadata", {})
                            )
                            self.feedback_cache.append(feedback)
                
                app_logger.info(f"加载了 {len(self.feedback_cache)} 条反馈记录")
        except Exception as e:
            app_logger.warning(f"加载反馈失败: {str(e)}")


# 全局反馈管理器实例
_feedback_manager: Optional[FeedbackManager] = None


def get_feedback_manager() -> FeedbackManager:
    """获取全局反馈管理器实例"""
    global _feedback_manager
    if _feedback_manager is None:
        _feedback_manager = FeedbackManager()
    return _feedback_manager

