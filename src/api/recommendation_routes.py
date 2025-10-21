"""
问法推荐API路由
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from src.utils import app_logger
from src.agent.recommendation_engine import (
    get_question_recommender, Recommendation, RecommendationType
)
from src.agent.recommendation_feedback import (
    get_feedback_manager, FeedbackType, UserAction
)


# ==================== 数据模型 ====================

class RecommendationRequest(BaseModel):
    """推荐请求模型"""
    session_id: str = Field(..., description="会话ID")
    current_message: str = Field(..., description="当前用户消息", min_length=1)
    conversation_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="对话历史"
    )
    num_recommendations: int = Field(
        default=3,
        ge=1,
        le=10,
        description="推荐数量"
    )
    include_follow_ups: bool = Field(
        default=True,
        description="是否包含后续问题"
    )
    include_related: bool = Field(
        default=True,
        description="是否包含相关问题"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "user-123",
                "current_message": "如何使用API",
                "conversation_history": [
                    {"role": "user", "content": "你好"},
                    {"role": "assistant", "content": "你好，有什么我可以帮助的吗？"}
                ],
                "num_recommendations": 3
            }
        }


class RecommendationItem(BaseModel):
    """推荐项"""
    id: str = Field(..., description="推荐ID")
    question: str = Field(..., description="推荐问题")
    reason: str = Field(..., description="推荐理由")
    type: str = Field(..., description="推荐类型")
    score: float = Field(..., description="综合评分")
    relevance_score: float = Field(..., description="相关性评分")
    answerability_score: float = Field(..., description="可解答性评分")
    confidence: float = Field(..., description="置信度")


class RecommendationResponse(BaseModel):
    """推荐响应模型"""
    session_id: str = Field(..., description="会话ID")
    recommendations: List[RecommendationItem] = Field(
        ...,
        description="推荐列表"
    )
    context_summary: str = Field(..., description="上下文摘要")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="元数据"
    )


class FeedbackRequest(BaseModel):
    """反馈请求模型"""
    recommendation_id: str = Field(..., description="推荐ID")
    session_id: str = Field(..., description="会话ID")
    feedback: str = Field(
        ...,
        description="反馈类型: helpful/not_helpful/irrelevant/duplicate"
    )
    user_action: str = Field(
        ...,
        description="用户行为: clicked/ignored/dismissed"
    )
    user_comment: Optional[str] = Field(
        None,
        description="用户评论"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "recommendation_id": "rec-001",
                "session_id": "user-123",
                "feedback": "helpful",
                "user_action": "clicked",
                "user_comment": "这个推荐很有帮助"
            }
        }


class FeedbackResponse(BaseModel):
    """反馈响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="消息")


class FeedbackStatsResponse(BaseModel):
    """反馈统计响应"""
    total_feedback: int = Field(..., description="总反馈数")
    feedback_types: Dict[str, int] = Field(..., description="反馈类型分布")
    user_actions: Dict[str, int] = Field(..., description="用户行为分布")
    helpful_rate: float = Field(..., description="有帮助率")
    click_rate: float = Field(..., description="点击率")
    average_feedback_per_session: float = Field(..., description="每个会话平均反馈数")


# ==================== 路由 ====================

router = APIRouter(prefix="/api/v1/recommendations", tags=["问法推荐"])


@router.post("/questions", response_model=RecommendationResponse, summary="获取推荐问题")
async def get_recommendations(request: RecommendationRequest) -> RecommendationResponse:
    """
    获取推荐问题
    
    根据当前对话上下文和用户消息，生成智能推荐问题。
    
    - **session_id**: 会话ID，用于追踪用户会话
    - **current_message**: 当前用户消息
    - **conversation_history**: 对话历史（可选）
    - **num_recommendations**: 推荐数量（1-10，默认3）
    """
    try:
        app_logger.info(
            f"获取推荐: session_id={request.session_id}, "
            f"message_length={len(request.current_message)}"
        )
        
        # 获取推荐引擎
        recommender = get_question_recommender()
        
        # 生成推荐
        recommendations = recommender.generate_recommendations(
            current_message=request.current_message,
            conversation_history=request.conversation_history,
            num_recommendations=request.num_recommendations
        )
        
        # 过滤推荐类型
        if not request.include_follow_ups:
            recommendations = [
                r for r in recommendations
                if r.recommendation_type != RecommendationType.FOLLOW_UP
            ]
        
        if not request.include_related:
            recommendations = [
                r for r in recommendations
                if r.recommendation_type != RecommendationType.RELATED
            ]
        
        # 转换为响应格式
        recommendation_items = [
            RecommendationItem(**r.to_dict())
            for r in recommendations
        ]
        
        # 生成上下文摘要
        context_summary = f"用户询问: {request.current_message[:100]}"
        if request.conversation_history:
            context_summary += f" (对话深度: {len(request.conversation_history)})"
        
        response = RecommendationResponse(
            session_id=request.session_id,
            recommendations=recommendation_items,
            context_summary=context_summary,
            metadata={
                "recommendation_count": len(recommendation_items),
                "average_score": round(
                    sum(r.score for r in recommendation_items) / len(recommendation_items)
                    if recommendation_items else 0,
                    3
                ),
            }
        )
        
        app_logger.info(
            f"推荐生成成功: {len(recommendation_items)} 个推荐, "
            f"平均评分: {response.metadata['average_score']}"
        )
        
        return response
        
    except Exception as e:
        app_logger.error(f"获取推荐失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取推荐失败: {str(e)}")


@router.post("/feedback", response_model=FeedbackResponse, summary="提交推荐反馈")
async def submit_feedback(request: FeedbackRequest) -> FeedbackResponse:
    """
    提交推荐反馈
    
    用户可以对推荐进行反馈，帮助系统优化推荐模型。
    
    - **recommendation_id**: 推荐ID
    - **session_id**: 会话ID
    - **feedback**: 反馈类型 (helpful/not_helpful/irrelevant/duplicate)
    - **user_action**: 用户行为 (clicked/ignored/dismissed)
    - **user_comment**: 用户评论（可选）
    """
    try:
        app_logger.info(
            f"提交反馈: rec_id={request.recommendation_id}, "
            f"feedback={request.feedback}, action={request.user_action}"
        )
        
        # 获取反馈管理器
        feedback_manager = get_feedback_manager()
        
        # 提交反馈
        success = feedback_manager.submit_feedback(
            recommendation_id=request.recommendation_id,
            session_id=request.session_id,
            feedback_type=request.feedback,
            user_action=request.user_action,
            user_comment=request.user_comment
        )
        
        if success:
            return FeedbackResponse(
                success=True,
                message="反馈已成功提交"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="反馈提交失败，请检查参数"
            )
        
    except ValueError as e:
        app_logger.error(f"无效的反馈参数: {str(e)}")
        raise HTTPException(status_code=400, detail=f"无效的参数: {str(e)}")
    except Exception as e:
        app_logger.error(f"提交反馈失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"提交反馈失败: {str(e)}")


@router.get("/stats", response_model=FeedbackStatsResponse, summary="获取反馈统计")
async def get_feedback_stats() -> FeedbackStatsResponse:
    """
    获取反馈统计信息
    
    返回推荐系统的反馈统计数据，包括有帮助率、点击率等指标。
    """
    try:
        feedback_manager = get_feedback_manager()
        stats = feedback_manager.get_feedback_stats()
        
        return FeedbackStatsResponse(**stats)
        
    except Exception as e:
        app_logger.error(f"获取反馈统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@router.get("/session/{session_id}/feedback", summary="获取会话反馈")
async def get_session_feedback(session_id: str) -> Dict[str, Any]:
    """
    获取特定会话的反馈
    
    - **session_id**: 会话ID
    """
    try:
        feedback_manager = get_feedback_manager()
        feedback_list = feedback_manager.get_session_feedback(session_id)
        
        return {
            "session_id": session_id,
            "feedback_count": len(feedback_list),
            "feedback": feedback_list
        }
        
    except Exception as e:
        app_logger.error(f"获取会话反馈失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取反馈失败: {str(e)}")


@router.get("/trends", summary="获取反馈趋势")
async def get_feedback_trends(limit: int = 100) -> Dict[str, Any]:
    """
    获取反馈趋势分析
    
    - **limit**: 分析的最近反馈数量（默认100）
    """
    try:
        feedback_manager = get_feedback_manager()
        trends = feedback_manager.analyze_feedback_trends(limit=limit)
        
        return trends
        
    except Exception as e:
        app_logger.error(f"获取反馈趋势失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取趋势失败: {str(e)}")

