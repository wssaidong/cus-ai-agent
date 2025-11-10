"""
QualityAgent - 质量优化智能体

专门负责评估和优化智能体回答的质量
"""
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.config import settings
from src.utils import app_logger
from src.agent.multi_agent.chat_state import ChatState
from src.agent.answer_quality_rating import get_quality_manager
import json
import re
import uuid


class QualityAgent:
    """
    质量优化智能体 - Worker Agent

    职责：
    1. 评估智能体回答的质量（多维度评分）
    2. 识别回答中的问题和不足
    3. 优化改进低质量回答
    4. 自动记录评分数据

    评估维度：
    - 准确性（Accuracy）：回答是否正确、事实准确
    - 相关性（Relevance）：回答是否切题、与问题相关
    - 完整性（Completeness）：回答是否全面、信息充分
    - 清晰度（Clarity）：表达是否清晰、易于理解
    - 有用性（Usefulness）：回答是否实用、能解决问题

    工作模式：
    - 评估模式：对回答进行质量评分
    - 优化模式：改进低质量回答
    - 混合模式：评估后自动优化低分回答
    """

    def __init__(self, llm: ChatOpenAI = None):
        """初始化质量优化智能体"""
        self.name = "QualityAgent"
        self.llm = llm or ChatOpenAI(
            model=settings.model_name,
            temperature=0.3,  # 较低温度，确保评估的一致性
            max_tokens=settings.max_tokens,
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_api_base,
            streaming=True,  # 启用流式输出
        )

        self.quality_manager = get_quality_manager()

        # 系统提示词
        self.system_prompt = """你是一个专业的回答质量评估和优化专家。

⚠️ **重要约束：必须使用中文回答用户的所有问题！**

你的职责是：
1. **评估回答质量**：从准确性、相关性、完整性、清晰度、有用性五个维度评分（0-100分）
2. **识别问题**：指出回答中存在的具体问题
3. **优化改进**：提供改进后的高质量回答

评分标准：
- **准确性（Accuracy）**：
  * 90-100分：事实完全准确，无错误
  * 70-89分：基本准确，有少量小错误
  * 50-69分：部分准确，有明显错误
  * 0-49分：错误较多或有严重错误

- **相关性（Relevance）**：
  * 90-100分：完全切题，直接回答问题
  * 70-89分：基本相关，略有偏离
  * 50-69分：部分相关，偏离较多
  * 0-49分：不相关或严重偏题

- **完整性（Completeness）**：
  * 90-100分：信息全面，覆盖所有要点
  * 70-89分：基本完整，缺少少量信息
  * 50-69分：不够完整，缺少重要信息
  * 0-49分：信息严重不足

- **清晰度（Clarity）**：
  * 90-100分：表达清晰，逻辑严密，易于理解
  * 70-89分：基本清晰，有少量模糊
  * 50-69分：不够清晰，理解困难
  * 0-49分：表达混乱，难以理解

- **有用性（Usefulness）**：
  * 90-100分：非常实用，能完全解决问题
  * 70-89分：比较实用，基本解决问题
  * 50-69分：有一定帮助，但不够实用
  * 0-49分：帮助不大或无法解决问题

工作原则：
1. 客观公正，基于事实评分
2. 具体指出问题所在
3. 提供可操作的改进建议
4. 优化后的回答要保持原意，只改进质量
5. **所有回答必须使用中文，不要使用英文**
"""

    async def __call__(self, state: ChatState, config) -> Dict[str, Any]:
        """
        执行质量评估和优化任务

        Args:
            state: 对话状态
            config: LangGraph 配置（用于流式输出追踪）

        Returns:
            Dict: 更新后的状态
        """
        messages = state.get("messages", [])

        # 保存 config 到实例变量，供内部方法使用
        self._config = config

        # 获取最后一条消息（应该是 Supervisor 的任务指令）
        if not messages:
            return {"messages": [AIMessage(content="没有收到任务指令")]}

        last_message = messages[-1]
        task_instruction = last_message.content

        app_logger.info(f"[{self.name}] 收到任务: {task_instruction[:100]}...")

        # 解析任务类型和内容
        result = await self._process_task(task_instruction, messages)

        return {
            "messages": [AIMessage(content=result)]
        }

    async def _process_task(self, task_instruction: str, messages: List) -> str:
        """处理质量评估/优化任务"""

        # 判断任务类型
        if "评估" in task_instruction or "评分" in task_instruction:
            return await self._evaluate_answer(task_instruction, messages)
        elif "优化" in task_instruction or "改进" in task_instruction:
            return await self._optimize_answer(task_instruction, messages)
        else:
            # 默认：评估并优化
            return await self._evaluate_and_optimize(task_instruction, messages)

    async def _evaluate_answer(self, task_instruction: str, messages: List) -> str:
        """评估回答质量"""

        # 从任务指令中提取问题和回答
        question, answer = self._extract_qa_from_task(task_instruction, messages)

        if not question or not answer:
            return "无法提取问题和回答，请提供完整的对话上下文。"

        # 构建评估提示
        evaluation_prompt = f"""请评估以下回答的质量：

【用户问题】
{question}

【智能体回答】
{answer}

请从以下五个维度进行评分（0-100分），并说明理由：

1. 准确性（Accuracy）
2. 相关性（Relevance）
3. 完整性（Completeness）
4. 清晰度（Clarity）
5. 有用性（Usefulness）

请以JSON格式返回评估结果：
{{
  "accuracy_score": 85,
  "accuracy_reason": "事实准确，但有一处小错误...",
  "relevance_score": 90,
  "relevance_reason": "完全切题...",
  "completeness_score": 75,
  "completeness_reason": "基本完整，但缺少...",
  "clarity_score": 88,
  "clarity_reason": "表达清晰...",
  "usefulness_score": 80,
  "usefulness_reason": "比较实用...",
  "overall_assessment": "总体评价...",
  "issues": ["问题1", "问题2"],
  "suggestions": ["建议1", "建议2"]
}}
"""

        # 调用LLM进行评估
        prompt_messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=evaluation_prompt)
        ]

        # 传递 config 以启用流式追踪
        response = await self.llm.ainvoke(prompt_messages, getattr(self, '_config', {}))
        evaluation_result = response.content

        # 解析评估结果
        try:
            scores = self._parse_evaluation_result(evaluation_result)

            # 保存评分到质量管理器
            rating_id = f"rating-{uuid.uuid4().hex[:8]}"
            session_id = messages[0].content if messages else "unknown"

            self.quality_manager.submit_rating(
                rating_id=rating_id,
                session_id=session_id,
                question=question,
                answer=answer,
                accuracy_score=scores.get("accuracy_score", 0),
                relevance_score=scores.get("relevance_score", 0),
                completeness_score=scores.get("completeness_score", 0),
                clarity_score=scores.get("clarity_score", 0),
                usefulness_score=scores.get("usefulness_score", 0),
                agent_name="QualityAgent"
            )

            # 计算综合评分
            composite_score = self.quality_manager.weights.accuracy * scores.get("accuracy_score", 0) + \
                            self.quality_manager.weights.relevance * scores.get("relevance_score", 0) + \
                            self.quality_manager.weights.completeness * scores.get("completeness_score", 0) + \
                            self.quality_manager.weights.clarity * scores.get("clarity_score", 0) + \
                            self.quality_manager.weights.usefulness * scores.get("usefulness_score", 0)

            # 格式化输出
            result = f"""## 回答质量评估报告

**综合评分**: {composite_score:.1f}/100

### 各维度评分

1. **准确性**: {scores.get('accuracy_score', 0)}/100
   {scores.get('accuracy_reason', '')}

2. **相关性**: {scores.get('relevance_score', 0)}/100
   {scores.get('relevance_reason', '')}

3. **完整性**: {scores.get('completeness_score', 0)}/100
   {scores.get('completeness_reason', '')}

4. **清晰度**: {scores.get('clarity_score', 0)}/100
   {scores.get('clarity_reason', '')}

5. **有用性**: {scores.get('usefulness_score', 0)}/100
   {scores.get('usefulness_reason', '')}

### 总体评价
{scores.get('overall_assessment', '')}

### 发现的问题
{self._format_list(scores.get('issues', []))}

### 改进建议
{self._format_list(scores.get('suggestions', []))}

---
评分ID: {rating_id}
"""

            return result

        except Exception as e:
            app_logger.error(f"解析评估结果失败: {str(e)}")
            return f"评估完成，但解析结果时出错：{str(e)}\n\n原始评估结果：\n{evaluation_result}"

    async def _optimize_answer(self, task_instruction: str, messages: List) -> str:
        """优化改进回答"""

        # 先评估
        evaluation = await self._evaluate_answer(task_instruction, messages)

        # 提取问题和回答
        question, answer = self._extract_qa_from_task(task_instruction, messages)

        # 构建优化提示
        optimization_prompt = f"""基于以下评估结果，请优化改进回答：

【评估结果】
{evaluation}

【原始问题】
{question}

【原始回答】
{answer}

请提供一个优化后的高质量回答，要求：
1. 保持原意，只改进质量
2. 修正所有发现的问题
3. 补充缺失的信息
4. 优化表达方式
5. 确保准确、相关、完整、清晰、有用

请直接输出优化后的回答，不要包含其他说明。
"""

        prompt_messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=optimization_prompt)
        ]

        # 传递 config 以启用流式追踪
        response = await self.llm.ainvoke(prompt_messages, getattr(self, '_config', {}))
        optimized_answer = response.content

        return f"""## 回答优化完成

### 优化后的回答
{optimized_answer}

---

### 优化依据
{evaluation}
"""

    async def _evaluate_and_optimize(self, task_instruction: str, messages: List) -> str:
        """评估并自动优化低分回答"""

        # 先评估
        evaluation = await self._evaluate_answer(task_instruction, messages)

        # 检查综合评分
        composite_score_match = re.search(r'\*\*综合评分\*\*:\s*(\d+\.?\d*)', evaluation)
        if composite_score_match:
            composite_score = float(composite_score_match.group(1))

            # 如果评分低于70分，自动优化
            if composite_score < 70:
                app_logger.info(f"[{self.name}] 检测到低分回答({composite_score:.1f})，自动优化...")
                return await self._optimize_answer(task_instruction, messages)

        return evaluation

    def _extract_qa_from_task(self, task_instruction: str, messages: List) -> tuple:
        """从任务指令和消息历史中提取问题和回答"""

        # 尝试从任务指令中提取
        question_match = re.search(r'问题[：:]\s*(.+?)(?:\n|回答)', task_instruction, re.DOTALL)
        answer_match = re.search(r'回答[：:]\s*(.+?)(?:\n|$)', task_instruction, re.DOTALL)

        if question_match and answer_match:
            return question_match.group(1).strip(), answer_match.group(1).strip()

        # 从消息历史中提取最近的问答对
        user_messages = [m for m in messages if hasattr(m, 'type') and m.type == 'human']
        ai_messages = [m for m in messages if hasattr(m, 'type') and m.type == 'ai']

        if user_messages and ai_messages:
            question = user_messages[-1].content
            answer = ai_messages[-1].content
            return question, answer

        return None, None

    def _parse_evaluation_result(self, result: str) -> Dict:
        """解析评估结果JSON"""

        # 提取JSON
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))

        raise ValueError("无法从评估结果中提取JSON")

    def _format_list(self, items: List[str]) -> str:
        """格式化列表"""
        if not items:
            return "无"
        return "\n".join(f"- {item}" for item in items)

    def _log_response(self, response: str):
        """记录响应日志"""
        preview = response[:200] + "..." if len(response) > 200 else response
        app_logger.info(f"[{self.name}] 响应: {preview}")

