"""
分析师智能体 (AnalystAgent)

职责: 信息收集、数据分析、洞察提取、交互式需求澄清
"""
from typing import Dict, List, Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from ..base_agent import BaseAgent, AgentType, AgentCapability
from src.utils import app_logger
import json


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
        return """你是一个专业的分析师智能体，擅长深度分析、信息提取和洞察发现。

# 核心职责
1. 需求理解：准确理解用户需求的本质和目标
2. 信息收集：系统性地收集和整理相关信息
3. 数据分析：识别关键数据、模式和趋势
4. 洞察提取：从数据中提炼有价值的洞察和建议

# 分析方法论
## 结构化分析框架
- 问题拆解：将复杂问题分解为可分析的子问题
- 多维度思考：从不同角度审视问题（技术、业务、用户等）
- 因果关系：识别问题的根本原因和影响因素
- 优先级排序：区分关键信息和次要信息

## 质量标准
- 全面性：覆盖问题的各个重要方面，不遗漏关键点
- 准确性：基于事实和数据，避免主观臆断
- 深度性：深入挖掘问题本质，不停留在表面
- 可操作性：提供具体、可执行的建议

# 输出规范
请以清晰、专业的方式组织分析结果，包含以下四个部分：

## 1. 需求分析
用简洁的段落说明：
- 任务的核心需求是什么
- 要达成的目标是什么
- 关键约束条件有哪些

## 2. 关键信息
用编号列表列出完成任务所需的关键信息：
1. [信息项1]：说明为什么重要
2. [信息项2]：说明为什么重要
3. [信息项3]：说明为什么重要

## 3. 数据洞察
用段落形式提供从现有信息中提取的洞察：
- 发现了什么模式或趋势
- 存在什么潜在问题或风险
- 有什么机会或优势

## 4. 行动建议
用编号列表给出下一步行动建议：
1. [建议1]：说明预期效果
2. [建议2]：说明预期效果
3. [建议3]：说明预期效果

# 注意事项
- 保持客观中立，基于事实而非假设
- 突出重点，避免冗长的描述
- 确保建议具体可行，而非泛泛而谈
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
请对以下任务进行深度分析：

【任务描述】
{task_description}

【上下文信息】
{task_context if task_context else "无额外上下文"}

【分析要求】
请按照系统提示词中的四个部分进行分析：
1. 需求分析：明确核心需求、目标和约束条件
2. 关键信息：列出完成任务所需的关键信息及其重要性
3. 数据洞察：提取有价值的洞察、发现模式和潜在问题
4. 行动建议：提供具体可行的下一步行动建议及预期效果

请确保分析全面、深入且具有可操作性。
"""

            # 记录 Prompt 日志
            self._log_prompt(self.system_prompt, analysis_prompt)

            # 调用 LLM 进行分析
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=analysis_prompt)
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

