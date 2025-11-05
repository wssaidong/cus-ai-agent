"""
研究员智能体 (ResearcherAgent)

职责: 深度研究、知识整合、报告生成
"""
from typing import Dict, List, Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.tools import BaseTool
from ..base_agent import BaseAgent, AgentType, AgentCapability
from src.utils import app_logger


class ResearcherAgent(BaseAgent):
    """
    研究员智能体

    能力:
    - 深度研究
    - 知识整合
    - 文档生成
    - 引用管理
    """

    def __init__(self, agent_id: str = "researcher_001", **kwargs):
        """初始化研究员智能体"""
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.RESEARCHER,
            name="研究员",
            description="负责深度研究、知识整合和报告生成",
            **kwargs
        )

    def _define_capabilities(self) -> List[AgentCapability]:
        """定义研究员能力"""
        return [
            AgentCapability(
                name="深度研究",
                description="对特定主题进行深入研究",
                required_tools=["knowledge_search", "web_search"],
                confidence=0.9
            ),
            AgentCapability(
                name="知识整合",
                description="整合多个来源的知识",
                confidence=0.85
            ),
            AgentCapability(
                name="文档生成",
                description="生成结构化的研究报告",
                confidence=0.85
            ),
            AgentCapability(
                name="引用管理",
                description="管理和引用信息来源",
                confidence=0.8
            ),
        ]

    def _get_default_system_prompt(self) -> str:
        """获取研究员系统提示词"""
        return """你是一个专业的研究员智能体。

你的职责:
1. 对特定主题进行深入研究
2. 从多个来源收集和整合知识
3. 生成结构化的研究报告
4. 提供准确的引用和来源

研究原则:
- 全面性: 覆盖主题的各个方面
- 深度性: 深入挖掘关键问题
- 准确性: 确保信息的准确性
- 可追溯: 提供清晰的引用

输出格式:
请以自然、流畅的对话方式输出研究结果。用简洁的段落和编号列表来组织内容。

包含以下内容：
1. 研究摘要：用一段话简要概述研究主题和核心内容
2. 关键发现：用编号列表（1. 2. 3.）列出重要的发现和洞察
3. 研究结论：用段落形式说明基于研究得出的结论
4. 参考来源：用编号列表列出信息来源（如果有）

"""

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理研究任务

        Args:
            state: 当前状态

        Returns:
            Dict[str, Any]: 研究结果
        """
        try:
            app_logger.info(f"{self.name} 开始研究任务")

            # 获取任务信息 - 兼容字典和字符串格式
            task = state.get("task", {})
            if isinstance(task, dict):
                task_description = task.get("description", "")
                research_topic = task.get("topic", task_description)
            elif isinstance(task, str):
                task_description = task
                research_topic = task
            else:
                task_description = str(task)
                research_topic = str(task)

            # 构建研究提示
            research_prompt = f"""
请对以下主题进行深入研究:

研究主题: {research_topic}

请提供:
1. 研究摘要: 主题的概述
2. 关键发现: 重要的发现和洞察
3. 结论: 基于研究的结论
4. 参考文献: 信息来源
"""

            # 记录 Prompt 日志
            self._log_prompt(self.system_prompt, research_prompt)

            # 调用 LLM 进行研究
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=research_prompt)
            ]

            response = await self.llm.ainvoke(messages)

            # 记录 Response 日志
            self._log_response(response.content)

            # 直接使用文本输出，不再解析 JSON
            # 构建返回结果
            result = {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "agent_name": self.name,
                "topic": research_topic,
                "research_output": response.content,  # 直接使用文本内容
                "success": True,
                "output": response.content  # 用户友好的文本输出
            }

            app_logger.info(f"{self.name} 研究完成")
            return result

        except Exception as e:
            app_logger.error(f"{self.name} 研究失败: {str(e)}")
            return {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "agent_name": self.name,
                "error": str(e),
                "success": False
            }

