"""
问法推荐引擎
用于生成智能的问法推荐，帮助用户更有效地利用智能体
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.config import settings
from src.utils import app_logger


class RecommendationType(Enum):
    """推荐类型"""
    FOLLOW_UP = "follow_up"           # 后续问题
    RELATED = "related"               # 相关问题
    CLARIFICATION = "clarification"   # 澄清问题
    KNOWLEDGE_BASED = "knowledge_based"  # 知识库推荐


@dataclass
class Recommendation:
    """推荐项"""
    id: str
    question: str
    reason: str
    recommendation_type: RecommendationType
    relevance_score: float = 0.0      # 相关性评分 0-1
    answerability_score: float = 0.0  # 可解答性评分 0-1
    user_interest_score: float = 0.5  # 用户兴趣评分 0-1
    confidence: float = 0.0           # 置信度 0-1
    
    @property
    def composite_score(self) -> float:
        """综合评分 = 0.4×相关性 + 0.3×可解答性 + 0.3×用户兴趣"""
        return (
            0.4 * self.relevance_score +
            0.3 * self.answerability_score +
            0.3 * self.user_interest_score
        )
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "question": self.question,
            "reason": self.reason,
            "type": self.recommendation_type.value,
            "score": round(self.composite_score, 3),
            "relevance_score": round(self.relevance_score, 3),
            "answerability_score": round(self.answerability_score, 3),
            "confidence": round(self.confidence, 3),
        }


@dataclass
class ContextAnalysis:
    """上下文分析结果"""
    main_topic: str                    # 主要话题
    user_intent: str                   # 用户意图
    keywords: List[str] = field(default_factory=list)  # 关键词
    entities: List[str] = field(default_factory=list)  # 实体
    conversation_depth: int = 0        # 对话深度


class QuestionRecommender:
    """问法推荐引擎"""
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        """
        初始化推荐引擎
        
        Args:
            llm: 语言模型，如果为None则使用默认配置
        """
        self.llm = llm or ChatOpenAI(
            model=settings.model_name,
            temperature=0.3,
            max_tokens=1000,
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_api_base,
        )
        self.recommendation_counter = 0
    
    def analyze_context(self, 
                       current_message: str,
                       conversation_history: List[Dict]) -> ContextAnalysis:
        """
        分析对话上下文
        
        Args:
            current_message: 当前用户消息
            conversation_history: 对话历史
            
        Returns:
            ContextAnalysis: 上下文分析结果
        """
        try:
            prompt = f"""分析以下对话上下文，提取关键信息。

当前消息: {current_message}

对话历史摘要:
{self._summarize_history(conversation_history)}

请以JSON格式返回分析结果，包含：
1. main_topic: 主要话题
2. user_intent: 用户意图 (inquiry/help/clarification/exploration)
3. keywords: 关键词列表 (最多5个)
4. entities: 实体列表 (最多5个)

返回格式示例：
{{
    "main_topic": "API使用",
    "user_intent": "inquiry",
    "keywords": ["API", "参数", "调用"],
    "entities": ["OpenAI API", "Python"]
}}

只返回JSON，不要其他文本。"""
            
            messages = [
                SystemMessage(content="你是一个对话分析专家。"),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            result = json.loads(response.content.strip())
            
            return ContextAnalysis(
                main_topic=result.get("main_topic", ""),
                user_intent=result.get("user_intent", "inquiry"),
                keywords=result.get("keywords", []),
                entities=result.get("entities", []),
                conversation_depth=len(conversation_history)
            )
        except Exception as e:
            app_logger.warning(f"上下文分析失败: {str(e)}")
            return ContextAnalysis(
                main_topic="",
                user_intent="inquiry",
                keywords=[],
                entities=[],
                conversation_depth=len(conversation_history)
            )
    
    def generate_recommendations(self,
                                current_message: str,
                                conversation_history: List[Dict],
                                num_recommendations: int = 3) -> List[Recommendation]:
        """
        生成推荐问题
        
        Args:
            current_message: 当前用户消息
            conversation_history: 对话历史
            num_recommendations: 推荐数量
            
        Returns:
            List[Recommendation]: 推荐列表
        """
        try:
            # 分析上下文
            context = self.analyze_context(current_message, conversation_history)
            
            # 生成候选推荐
            candidates = self._generate_candidates(
                current_message, context, num_recommendations
            )
            
            # 评分和排序
            scored_recommendations = self._score_recommendations(
                candidates, context, current_message
            )
            
            # 排序并返回
            sorted_recs = sorted(
                scored_recommendations,
                key=lambda x: x.composite_score,
                reverse=True
            )[:num_recommendations]
            
            app_logger.info(
                f"生成了 {len(sorted_recs)} 个推荐，"
                f"平均评分: {sum(r.composite_score for r in sorted_recs) / len(sorted_recs):.2f}"
            )
            
            return sorted_recs
            
        except Exception as e:
            app_logger.error(f"生成推荐失败: {str(e)}")
            return []
    
    def _summarize_history(self, history: List[Dict]) -> str:
        """总结对话历史"""
        if not history:
            return "无对话历史"
        
        summary_lines = []
        for item in history[-3:]:  # 只取最后3条
            role = item.get("role", "unknown")
            content = item.get("content", "")[:100]  # 截断到100字符
            summary_lines.append(f"{role}: {content}")
        
        return "\n".join(summary_lines)
    
    def _generate_candidates(self,
                            current_message: str,
                            context: ContextAnalysis,
                            num_recommendations: int) -> List[Recommendation]:
        """生成候选推荐"""
        try:
            prompt = f"""基于以下对话上下文，生成 {num_recommendations} 个推荐问题。

当前消息: {current_message}
主要话题: {context.main_topic}
用户意图: {context.user_intent}
关键词: {', '.join(context.keywords)}

请生成不同类型的推荐问题：
1. 后续问题 (follow_up): 自然延伸的问题
2. 相关问题 (related): 相关话题的问题
3. 澄清问题 (clarification): 帮助澄清的问题

返回JSON格式：
{{
    "recommendations": [
        {{
            "question": "推荐问题",
            "type": "follow_up|related|clarification",
            "reason": "推荐理由"
        }}
    ]
}}

只返回JSON，不要其他文本。"""
            
            messages = [
                SystemMessage(content="你是一个问题推荐专家。生成有用的后续问题。"),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            result = json.loads(response.content.strip())
            
            candidates = []
            for item in result.get("recommendations", []):
                self.recommendation_counter += 1
                rec = Recommendation(
                    id=f"rec-{self.recommendation_counter}",
                    question=item.get("question", ""),
                    reason=item.get("reason", ""),
                    recommendation_type=RecommendationType(item.get("type", "follow_up"))
                )
                candidates.append(rec)
            
            return candidates
            
        except Exception as e:
            app_logger.warning(f"生成候选推荐失败: {str(e)}")
            return []
    
    def _score_recommendations(self,
                              recommendations: List[Recommendation],
                              context: ContextAnalysis,
                              current_message: str) -> List[Recommendation]:
        """对推荐进行评分"""
        for rec in recommendations:
            # 相关性评分
            rec.relevance_score = self._calculate_relevance_score(
                rec.question, context
            )
            
            # 可解答性评分
            rec.answerability_score = self._calculate_answerability_score(
                rec.question
            )
            
            # 置信度
            rec.confidence = min(
                rec.relevance_score * 0.6 + rec.answerability_score * 0.4,
                1.0
            )
        
        return recommendations
    
    def _calculate_relevance_score(self,
                                  question: str,
                                  context: ContextAnalysis) -> float:
        """计算相关性评分"""
        score = 0.5  # 基础分
        
        # 检查关键词匹配
        question_lower = question.lower()
        keyword_matches = sum(
            1 for kw in context.keywords
            if kw.lower() in question_lower
        )
        score += keyword_matches * 0.1
        
        # 检查话题相关性
        if context.main_topic.lower() in question_lower:
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_answerability_score(self, question: str) -> float:
        """计算可解答性评分"""
        # 简单启发式：问题越具体，可解答性越高
        score = 0.5
        
        # 检查问题长度
        if len(question) > 20:
            score += 0.2
        
        # 检查问号
        if "?" in question:
            score += 0.1
        
        # 检查具体词汇
        specific_words = ["如何", "怎样", "什么", "哪个", "为什么"]
        if any(word in question for word in specific_words):
            score += 0.2
        
        return min(score, 1.0)


# 全局推荐引擎实例
_recommender: Optional[QuestionRecommender] = None


def get_question_recommender() -> QuestionRecommender:
    """获取全局推荐引擎实例"""
    global _recommender
    if _recommender is None:
        _recommender = QuestionRecommender()
    return _recommender

