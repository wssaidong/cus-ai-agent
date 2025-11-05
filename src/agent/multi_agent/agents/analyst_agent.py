"""
分析师智能体 (AnalystAgent)

职责: 信息收集、数据分析、洞察提取
"""
from typing import Dict, List, Any
from langchain_core.messages import HumanMessage, SystemMessage
from ..base_agent import BaseAgent, AgentType, AgentCapability
from src.utils import app_logger


class AnalystAgent(BaseAgent):
    """
    分析师智能体

    能力:
    - 需求分析
    - 信息检索
    - 数据分析
    - 趋势识别
    """

    def __init__(self, agent_id: str = "analyst_001", **kwargs):
        """初始化分析师智能体"""
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.ANALYST,
            name="分析师",
            description="负责信息收集、数据分析和洞察提取",
            **kwargs
        )

    def _define_capabilities(self) -> List[AgentCapability]:
        """定义分析师能力"""
        return [
            AgentCapability(
                name="需求分析",
                description="分析用户需求,提取关键信息",
                confidence=0.9
            ),
            AgentCapability(
                name="信息检索",
                description="从知识库和外部源检索相关信息",
                required_tools=["knowledge_search", "web_search"],
                confidence=0.85
            ),
            AgentCapability(
                name="数据分析",
                description="分析数据,识别模式和趋势",
                confidence=0.8
            ),
            AgentCapability(
                name="洞察提取",
                description="从数据中提取有价值的洞察",
                confidence=0.85
            ),
        ]

    def _get_default_system_prompt(self) -> str:
        """获取分析师系统提示词"""
        return """你是一个专业的分析师智能体。

你的职责:
1. 深入分析用户需求和问题
2. 收集和整理相关信息
3. 识别关键数据和模式
4. 提取有价值的洞察

分析原则:
- 全面性: 考虑问题的各个方面
- 准确性: 基于事实和数据进行分析
- 深度性: 深入挖掘问题本质
- 结构化: 以清晰的结构呈现分析结果

输出格式:
请以自然、流畅的对话方式输出分析结果。用简洁的段落和编号列表来组织内容。

包含以下内容：
1. 需求分析：用一段话明确说明任务的核心需求和目标
2. 关键信息：用编号列表（1. 2. 3.）列出完成任务所需的关键信息
3. 数据洞察：用段落形式提供从现有信息中提取的洞察
4. 建议：用编号列表（1. 2. 3.）给出下一步行动建议

注意：
- 不要使用 JSON 格式
- 不要使用 Markdown 标记（如 ###、**、- 等）
- 使用简洁、清晰的语言
- 直接输出内容，像在和用户对话一样自然
"""

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理分析任务

        Args:
            state: 当前状态

        Returns:
            Dict[str, Any]: 分析结果
        """
        try:
            app_logger.info(f"{self.name} 开始分析任务")

            # 获取任务信息 - 兼容字典和字符串格式
            task = state.get("task", {})
            if isinstance(task, dict):
                task_description = task.get("description", "")
                task_context = task.get("context", "")
            elif isinstance(task, str):
                task_description = task
                task_context = ""
            else:
                task_description = str(task)
                task_context = ""

            # 构建分析提示
            analysis_prompt = f"""
请分析以下任务:

任务描述: {task_description}

上下文信息: {task_context}

请提供:
1. 需求分析: 明确任务的核心需求和目标
2. 关键信息: 识别完成任务所需的关键信息
3. 数据洞察: 从现有信息中提取洞察
4. 建议: 提供下一步行动建议
"""

            # 调用 LLM 进行分析
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=analysis_prompt)
            ]

            response = await self.llm.ainvoke(messages)

            # 直接使用文本输出，不再解析 JSON
            # 构建返回结果
            result = {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "agent_name": self.name,
                "analysis": response.content,  # 直接使用文本内容
                "success": True,
                "output": response.content  # 用户友好的文本输出
            }

            app_logger.info(f"{self.name} 分析完成")
            return result

        except Exception as e:
            app_logger.error(f"{self.name} 分析失败: {str(e)}")
            return {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "agent_name": self.name,
                "error": str(e),
                "success": False
            }

    async def analyze_requirements(self, requirements: str) -> Dict[str, Any]:
        """
        分析需求

        Args:
            requirements: 需求描述

        Returns:
            Dict[str, Any]: 需求分析结果
        """
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"请分析以下需求:\n{requirements}")
        ]

        response = await self.llm.ainvoke(messages)

        return {
            "requirements": requirements,
            "analysis": response.content,
            "agent_id": self.agent_id
        }

    async def extract_insights(self, data: Any) -> Dict[str, Any]:
        """
        提取洞察

        Args:
            data: 数据

        Returns:
            Dict[str, Any]: 洞察结果
        """
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"请从以下数据中提取洞察:\n{data}")
        ]

        response = await self.llm.ainvoke(messages)

        return {
            "data": data,
            "insights": response.content,
            "agent_id": self.agent_id
        }

