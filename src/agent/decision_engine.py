"""
智能决策引擎
用于判断问题应走知识检索还是工具调用
"""
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.config import settings
from src.utils import app_logger
import json


class DecisionType(Enum):
    """决策类型"""
    KNOWLEDGE_BASE = "knowledge_base"  # 知识库搜索
    GENERAL_CHAT = "general_chat"  # 通用对话
    MULTI_TOOL = "multi_tool"  # 多工具组合


@dataclass
class DecisionResult:
    """决策结果"""
    decision_type: DecisionType
    confidence: float  # 置信度 0-1
    reasoning: str  # 推理过程
    recommended_tools: List[str]  # 推荐工具列表
    should_search_kb: bool  # 是否应该搜索知识库


class DecisionEngine:
    """智能决策引擎"""

    def __init__(self, llm: Optional[ChatOpenAI] = None):
        """
        初始化决策引擎

        Args:
            llm: 语言模型，如果为None则使用默认配置
        """
        self.llm = llm or ChatOpenAI(
            model=settings.model_name,
            temperature=0.3,  # 降低温度以获得更一致的决策
            max_tokens=500,
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_api_base,
        )

        # 定义问题类型的关键词
        self.knowledge_keywords = {
            "文档", "资料", "手册", "规范", "标准", "说明", "指南",
            "API", "接口", "功能", "配置", "参数", "属性",
            "如何", "怎么", "什么是", "怎样", "方法", "步骤",
            "教程", "流程", "定义", "概念", "术语", "解释",
            "知识库", "查询", "搜索", "查找", "了解", "学习",
            "文件", "文本", "内容", "信息", "数据", "记录"
        }



    def _keyword_match_score(self, query: str, keywords: set) -> float:
        """
        计算关键词匹配分数

        Args:
            query: 查询文本
            keywords: 关键词集合

        Returns:
            匹配分数 0-1
        """
        query_lower = query.lower()
        matched = sum(1 for kw in keywords if kw in query_lower)
        return min(matched / max(len(keywords), 1), 1.0)

    def _analyze_with_llm(self, query: str) -> Dict:
        """
        使用LLM分析问题类型

        Args:
            query: 用户查询

        Returns:
            分析结果字典
        """
        try:
            analysis_prompt = f"""分析以下用户查询，判断应该使用哪种工具或方法来回答。

用户查询：{query}

请以JSON格式返回分析结果，包含以下字段：
1. primary_type: 主要问题类型 (knowledge_base/calculator/text_process/api_call/general_chat/multi_tool)
2. confidence: 置信度 (0-1之间的数字)
3. reasoning: 简短的推理说明
4. secondary_types: 次要问题类型列表 (可选)
5. should_search_kb: 是否应该搜索知识库 (true/false)

返回格式示例：
{{
    "primary_type": "knowledge_base",
    "confidence": 0.95,
    "reasoning": "用户询问API配置方法，这是典型的知识库查询",
    "secondary_types": [],
    "should_search_kb": true
}}

只返回JSON，不要其他文本。"""

            messages = [
                SystemMessage(content="你是一个问题分类专家。分析用户查询并判断应该使用哪种工具。"),
                HumanMessage(content=analysis_prompt)
            ]

            response = self.llm.invoke(messages)
            response_text = response.content.strip()

            # 尝试解析JSON
            result = json.loads(response_text)
            return result

        except json.JSONDecodeError as e:
            app_logger.warning(f"LLM返回的JSON解析失败: {str(e)}")
            return {}
        except Exception as e:
            app_logger.error(f"LLM分析失败: {str(e)}")
            return {}

    def decide(self, query: str) -> DecisionResult:
        """
        智能决策：判断问题应走知识检索还是工具调用

        Args:
            query: 用户查询

        Returns:
            DecisionResult: 决策结果
        """
        try:
            # 第一步：关键词匹配评分
            kb_score = self._keyword_match_score(query, self.knowledge_keywords)

            app_logger.debug(
                f"关键词匹配分数 - KB: {kb_score:.2f}"
            )

            # 第二步：使用LLM进行深度分析
            llm_analysis = self._analyze_with_llm(query)

            # 第三步：综合决策
            if llm_analysis:
                primary_type = llm_analysis.get("primary_type", "general_chat")
                confidence = llm_analysis.get("confidence", 0.5)
                reasoning = llm_analysis.get("reasoning", "")
                should_search_kb = llm_analysis.get("should_search_kb", False)
            else:
                # 如果LLM分析失败，使用关键词匹配结果
                # 优先级：knowledge_base > general_chat
                scores = {
                    DecisionType.KNOWLEDGE_BASE: kb_score,
                }

                # 找到最高分的类型
                best_type = max(scores, key=scores.get)
                best_score = scores[best_type]

                if best_score > 0.3:
                    primary_type = best_type.value
                    confidence = best_score
                    reasoning = f"基于关键词匹配，推荐使用 {best_type.value}"
                    should_search_kb = best_type == DecisionType.KNOWLEDGE_BASE
                else:
                    primary_type = "general_chat"
                    confidence = 0.5
                    reasoning = "未匹配到特定工具，使用通用对话"
                    should_search_kb = False

            # 构建推荐工具列表
            recommended_tools = self._build_tool_list(primary_type, llm_analysis)

            # 创建决策结果
            decision_type = DecisionType(primary_type)
            result = DecisionResult(
                decision_type=decision_type,
                confidence=confidence,
                reasoning=reasoning,
                recommended_tools=recommended_tools,
                should_search_kb=should_search_kb or decision_type == DecisionType.KNOWLEDGE_BASE
            )

            app_logger.info(
                f"决策结果 - 类型: {decision_type.value}, "
                f"置信度: {confidence:.2%}, 推荐工具: {recommended_tools}"
            )

            return result

        except Exception as e:
            app_logger.error(f"决策引擎执行失败: {str(e)}")
            # 返回默认决策
            return DecisionResult(
                decision_type=DecisionType.GENERAL_CHAT,
                confidence=0.5,
                reasoning=f"决策引擎出错: {str(e)}",
                recommended_tools=[],
                should_search_kb=False
            )

    def _build_tool_list(self, primary_type: str, llm_analysis: Dict) -> List[str]:
        """
        构建推荐工具列表

        Args:
            primary_type: 主要问题类型
            llm_analysis: LLM分析结果

        Returns:
            推荐工具列表
        """
        tools = []

        # 添加主要工具
        if primary_type == "knowledge_base":
            tools.append("knowledge_base_search")
        elif primary_type == "multi_tool":
            # 多工具组合
            secondary = llm_analysis.get("secondary_types", [])
            if "knowledge_base" in secondary:
                tools.append("knowledge_base_search")

        return tools


# 全局决策引擎实例
_decision_engine: Optional[DecisionEngine] = None


def get_decision_engine() -> DecisionEngine:
    """获取全局决策引擎实例"""
    global _decision_engine
    if _decision_engine is None:
        _decision_engine = DecisionEngine()
    return _decision_engine

