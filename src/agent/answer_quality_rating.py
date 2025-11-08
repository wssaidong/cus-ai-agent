"""
智能体回答质量评分系统
用于评估、调整和跟踪智能体回答的质量
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
from src.utils import app_logger


class QualityDimension(Enum):
    """质量评分维度"""
    ACCURACY = "accuracy"           # 准确性：回答是否正确、事实准确
    RELEVANCE = "relevance"         # 相关性：回答是否切题、与问题相关
    COMPLETENESS = "completeness"   # 完整性：回答是否全面、信息充分
    CLARITY = "clarity"             # 清晰度：表达是否清晰、易于理解
    USEFULNESS = "usefulness"       # 有用性：回答是否实用、能解决问题


@dataclass
class RatingWeights:
    """评分权重配置"""
    accuracy: float = 0.30      # 准确性权重 30%
    relevance: float = 0.25     # 相关性权重 25%
    completeness: float = 0.20  # 完整性权重 20%
    clarity: float = 0.15       # 清晰度权重 15%
    usefulness: float = 0.10    # 有用性权重 10%
    
    def __post_init__(self):
        """验证权重总和为1.0"""
        total = (self.accuracy + self.relevance + self.completeness + 
                self.clarity + self.usefulness)
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"权重总和必须为1.0，当前为{total}")
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            "accuracy": self.accuracy,
            "relevance": self.relevance,
            "completeness": self.completeness,
            "clarity": self.clarity,
            "usefulness": self.usefulness,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'RatingWeights':
        """从字典创建"""
        return cls(
            accuracy=data.get("accuracy", 0.30),
            relevance=data.get("relevance", 0.25),
            completeness=data.get("completeness", 0.20),
            clarity=data.get("clarity", 0.15),
            usefulness=data.get("usefulness", 0.10),
        )


@dataclass
class AnswerQualityRating:
    """回答质量评分"""
    rating_id: str
    session_id: str
    question: str
    answer: str
    
    # 各维度评分 (0-100)
    accuracy_score: float = 0.0
    relevance_score: float = 0.0
    completeness_score: float = 0.0
    clarity_score: float = 0.0
    usefulness_score: float = 0.0
    
    # 元数据
    response_time: Optional[float] = None  # 响应时间（秒）
    user_id: Optional[str] = None
    agent_name: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    user_comment: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_composite_score(self, weights: RatingWeights) -> float:
        """
        计算综合评分
        
        Args:
            weights: 权重配置
            
        Returns:
            float: 综合评分 (0-100)
        """
        return (
            self.accuracy_score * weights.accuracy +
            self.relevance_score * weights.relevance +
            self.completeness_score * weights.completeness +
            self.clarity_score * weights.clarity +
            self.usefulness_score * weights.usefulness
        )
    
    def get_dimension_scores(self) -> Dict[str, float]:
        """获取各维度评分"""
        return {
            "accuracy": self.accuracy_score,
            "relevance": self.relevance_score,
            "completeness": self.completeness_score,
            "clarity": self.clarity_score,
            "usefulness": self.usefulness_score,
        }
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "rating_id": self.rating_id,
            "session_id": self.session_id,
            "question": self.question,
            "answer": self.answer,
            "accuracy_score": self.accuracy_score,
            "relevance_score": self.relevance_score,
            "completeness_score": self.completeness_score,
            "clarity_score": self.clarity_score,
            "usefulness_score": self.usefulness_score,
            "response_time": self.response_time,
            "user_id": self.user_id,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp,
            "user_comment": self.user_comment,
            "metadata": self.metadata,
        }


class AnswerQualityManager:
    """回答质量管理器"""
    
    def __init__(self, 
                 storage_path: Optional[str] = None,
                 weights: Optional[RatingWeights] = None):
        """
        初始化质量管理器
        
        Args:
            storage_path: 评分存储路径，默认为 ./data/answer_quality_ratings.jsonl
            weights: 评分权重配置，默认使用标准权重
        """
        self.storage_path = Path(storage_path or "./data/answer_quality_ratings.jsonl")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.weights = weights or RatingWeights()
        self.ratings_cache: List[AnswerQualityRating] = []
        self._load_ratings()
    
    def submit_rating(self,
                     rating_id: str,
                     session_id: str,
                     question: str,
                     answer: str,
                     accuracy_score: float = 0.0,
                     relevance_score: float = 0.0,
                     completeness_score: float = 0.0,
                     clarity_score: float = 0.0,
                     usefulness_score: float = 0.0,
                     response_time: Optional[float] = None,
                     user_id: Optional[str] = None,
                     agent_name: Optional[str] = None,
                     user_comment: Optional[str] = None,
                     metadata: Optional[Dict] = None) -> bool:
        """
        提交回答质量评分
        
        Args:
            rating_id: 评分ID
            session_id: 会话ID
            question: 用户问题
            answer: 智能体回答
            accuracy_score: 准确性评分 (0-100)
            relevance_score: 相关性评分 (0-100)
            completeness_score: 完整性评分 (0-100)
            clarity_score: 清晰度评分 (0-100)
            usefulness_score: 有用性评分 (0-100)
            response_time: 响应时间（秒）
            user_id: 用户ID
            agent_name: 智能体名称
            user_comment: 用户评论
            metadata: 额外元数据
            
        Returns:
            bool: 是否成功提交
        """
        try:
            # 验证评分范围
            scores = [accuracy_score, relevance_score, completeness_score, 
                     clarity_score, usefulness_score]
            for score in scores:
                if not 0 <= score <= 100:
                    raise ValueError(f"评分必须在0-100之间，当前值: {score}")
            
            rating = AnswerQualityRating(
                rating_id=rating_id,
                session_id=session_id,
                question=question,
                answer=answer,
                accuracy_score=accuracy_score,
                relevance_score=relevance_score,
                completeness_score=completeness_score,
                clarity_score=clarity_score,
                usefulness_score=usefulness_score,
                response_time=response_time,
                user_id=user_id,
                agent_name=agent_name,
                user_comment=user_comment,
                metadata=metadata or {}
            )
            
            self.ratings_cache.append(rating)
            self._save_rating(rating)
            
            composite_score = rating.calculate_composite_score(self.weights)
            app_logger.info(
                f"评分已提交: {rating_id} - 综合评分: {composite_score:.2f}"
            )
            
            return True
            
        except ValueError as e:
            app_logger.error(f"无效的评分参数: {str(e)}")
            return False
        except Exception as e:
            app_logger.error(f"提交评分失败: {str(e)}")
            return False
    
    def get_rating_stats(self) -> Dict:
        """
        获取评分统计信息
        
        Returns:
            Dict: 统计数据
        """
        if not self.ratings_cache:
            return {
                "total_ratings": 0,
                "average_composite_score": 0.0,
                "dimension_averages": {},
                "score_distribution": {},
                "low_score_count": 0,
            }
        
        total = len(self.ratings_cache)
        
        # 计算综合评分平均值
        composite_scores = [
            r.calculate_composite_score(self.weights) 
            for r in self.ratings_cache
        ]
        avg_composite = sum(composite_scores) / total
        
        # 计算各维度平均分
        dimension_averages = {
            "accuracy": sum(r.accuracy_score for r in self.ratings_cache) / total,
            "relevance": sum(r.relevance_score for r in self.ratings_cache) / total,
            "completeness": sum(r.completeness_score for r in self.ratings_cache) / total,
            "clarity": sum(r.clarity_score for r in self.ratings_cache) / total,
            "usefulness": sum(r.usefulness_score for r in self.ratings_cache) / total,
        }
        
        # 评分分布（优秀>=80, 良好>=60, 及格>=40, 不及格<40）
        score_distribution = {
            "excellent": sum(1 for s in composite_scores if s >= 80),
            "good": sum(1 for s in composite_scores if 60 <= s < 80),
            "fair": sum(1 for s in composite_scores if 40 <= s < 60),
            "poor": sum(1 for s in composite_scores if s < 40),
        }
        
        # 低分预警（<60分）
        low_score_count = sum(1 for s in composite_scores if s < 60)
        
        return {
            "total_ratings": total,
            "average_composite_score": round(avg_composite, 2),
            "dimension_averages": {k: round(v, 2) for k, v in dimension_averages.items()},
            "score_distribution": score_distribution,
            "low_score_count": low_score_count,
            "low_score_rate": round(low_score_count / total, 3) if total > 0 else 0.0,
        }
    
    def update_weights(self, new_weights: Dict[str, float]) -> bool:
        """
        更新评分权重
        
        Args:
            new_weights: 新的权重配置
            
        Returns:
            bool: 是否成功更新
        """
        try:
            self.weights = RatingWeights.from_dict(new_weights)
            app_logger.info(f"权重已更新: {self.weights.to_dict()}")
            return True
        except ValueError as e:
            app_logger.error(f"无效的权重配置: {str(e)}")
            return False
    
    def get_weights(self) -> Dict[str, float]:
        """获取当前权重配置"""
        return self.weights.to_dict()
    
    def _save_rating(self, rating: AnswerQualityRating) -> None:
        """保存评分到文件"""
        try:
            with open(self.storage_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rating.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            app_logger.error(f"保存评分失败: {str(e)}")
    
    def _load_ratings(self) -> None:
        """从文件加载评分"""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            rating = AnswerQualityRating(
                                rating_id=data["rating_id"],
                                session_id=data["session_id"],
                                question=data["question"],
                                answer=data["answer"],
                                accuracy_score=data.get("accuracy_score", 0.0),
                                relevance_score=data.get("relevance_score", 0.0),
                                completeness_score=data.get("completeness_score", 0.0),
                                clarity_score=data.get("clarity_score", 0.0),
                                usefulness_score=data.get("usefulness_score", 0.0),
                                response_time=data.get("response_time"),
                                user_id=data.get("user_id"),
                                agent_name=data.get("agent_name"),
                                timestamp=data.get("timestamp", datetime.now().isoformat()),
                                user_comment=data.get("user_comment"),
                                metadata=data.get("metadata", {})
                            )
                            self.ratings_cache.append(rating)
                
                app_logger.info(f"加载了 {len(self.ratings_cache)} 条评分记录")
        except Exception as e:
            app_logger.warning(f"加载评分失败: {str(e)}")


# 全局质量管理器实例
_quality_manager: Optional[AnswerQualityManager] = None


def get_quality_manager() -> AnswerQualityManager:
    """获取全局质量管理器实例"""
    global _quality_manager
    if _quality_manager is None:
        _quality_manager = AnswerQualityManager()
    return _quality_manager
