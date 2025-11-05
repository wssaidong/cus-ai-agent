"""
规划师智能体 (PlannerAgent)

职责: 任务分解、策略制定、计划优化
"""
from typing import Dict, List, Any
from langchain_core.messages import HumanMessage, SystemMessage
from ..base_agent import BaseAgent, AgentType, AgentCapability
from src.utils import app_logger


class PlannerAgent(BaseAgent):
    """
    规划师智能体

    能力:
    - 任务分解
    - 策略规划
    - 资源分配
    - 风险评估
    """

    def __init__(self, agent_id: str = "planner_001", **kwargs):
        """初始化规划师智能体"""
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.PLANNER,
            name="规划师",
            description="负责任务分解、策略制定和计划优化",
            **kwargs
        )

    def _define_capabilities(self) -> List[AgentCapability]:
        """定义规划师能力"""
        return [
            AgentCapability(
                name="任务分解",
                description="将复杂任务分解为可执行的子任务",
                confidence=0.9
            ),
            AgentCapability(
                name="策略规划",
                description="制定任务执行策略和方案",
                confidence=0.85
            ),
            AgentCapability(
                name="资源分配",
                description="合理分配资源和智能体",
                confidence=0.8
            ),
            AgentCapability(
                name="风险评估",
                description="评估执行风险并制定应对措施",
                confidence=0.75
            ),
        ]

    def _get_default_system_prompt(self) -> str:
        """获取规划师系统提示词"""
        return """你是一个专业的规划师智能体。

你的职责:
1. 分解复杂任务为可执行的子任务
2. 制定清晰的执行策略和计划
3. 合理分配资源和智能体
4. 评估风险并制定应对措施

规划原则:
- 可行性: 计划必须可执行
- 完整性: 覆盖任务的所有方面
- 优先级: 明确任务的优先级
- 灵活性: 考虑可能的变化和调整

输出格式:
请以自然、流畅的对话方式输出规划结果。用简洁的段落和编号列表来组织内容。

包含以下内容：
1. 执行计划：将任务分解为具体的执行步骤，每个步骤用编号列表（步骤1、步骤2）说明：
   - 步骤描述
   - 优先级（高/中/低）
   - 预计时间
2. 执行策略：用一段话说明如何执行这些步骤
3. 风险评估：用编号列表列出可能的风险和应对措施
4. 资源需求：用编号列表列出需要的资源和工具

"""

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理规划任务

        Args:
            state: 当前状态

        Returns:
            Dict[str, Any]: 规划结果
        """
        try:
            app_logger.info(f"{self.name} 开始规划任务")

            # 获取任务信息 - 兼容字典和字符串格式
            task = state.get("task", {})
            if isinstance(task, dict):
                task_description = task.get("description", "")
            elif isinstance(task, str):
                task_description = task
            else:
                task_description = str(task)

            # 获取分析结果(如果有)
            agent_results = state.get("agent_results", {})
            analysis = None
            for agent_id, result in agent_results.items():
                if "analyst" in agent_id:
                    analysis = result.get("analysis", {})
                    break

            # 构建规划提示
            planning_prompt = f"""
请为以下任务制定详细的执行计划:

任务描述: {task_description}
"""

            if analysis:
                planning_prompt += f"\n分析结果: {analysis}\n"

            planning_prompt += """
请提供:
1. 任务分解: 将任务分解为具体的执行步骤
2. 执行策略: 说明如何执行这些步骤
3. 风险评估: 识别可能的风险
4. 资源需求: 列出需要的资源和工具
"""

            # 记录 Prompt 日志
            self._log_prompt(self.system_prompt, planning_prompt)

            # 调用 LLM 进行规划
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=planning_prompt)
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
                "plan": response.content,  # 直接使用文本内容
                "success": True,
                "output": response.content  # 用户友好的文本输出
            }

            app_logger.info(f"{self.name} 规划完成")
            return result

        except Exception as e:
            app_logger.error(f"{self.name} 规划失败: {str(e)}")
            return {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "agent_name": self.name,
                "error": str(e),
                "success": False
            }

