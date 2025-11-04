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
请以 JSON 格式输出研究结果,包含以下字段:
{
    "topic": "研究主题",
    "summary": "研究摘要",
    "findings": [
        {
            "title": "发现标题",
            "content": "发现内容",
            "sources": ["来源1", "来源2"]
        }
    ],
    "conclusions": ["结论1", "结论2"],
    "references": ["参考文献1", "参考文献2"]
}
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
            
            # 获取任务信息
            task = state.get("task", {})
            task_description = task.get("description", "")
            research_topic = task.get("topic", task_description)
            
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
            
            # 调用 LLM 进行研究
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=research_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # 解析结果
            import json
            try:
                research_result = json.loads(response.content)
            except json.JSONDecodeError:
                research_result = {
                    "topic": research_topic,
                    "summary": response.content,
                    "raw_output": True
                }
            
            # 构建返回结果
            result = {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "agent_name": self.name,
                "topic": research_result.get("topic", research_topic),
                "summary": research_result.get("summary", ""),
                "findings": research_result.get("findings", []),
                "conclusions": research_result.get("conclusions", []),
                "references": research_result.get("references", []),
                "success": True,
                "output": response.content
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
    
    async def research_topic(self, topic: str) -> Dict[str, Any]:
        """
        研究特定主题
        
        Args:
            topic: 研究主题
            
        Returns:
            Dict[str, Any]: 研究结果
        """
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"请深入研究以下主题:\n{topic}")
        ]
        
        response = await self.llm.ainvoke(messages)
        
        import json
        try:
            result = json.loads(response.content)
            return result
        except:
            return {
                "topic": topic,
                "research": response.content,
                "agent_id": self.agent_id
            }
    
    async def generate_report(self, research_data: Dict[str, Any]) -> str:
        """
        生成研究报告
        
        Args:
            research_data: 研究数据
            
        Returns:
            str: 研究报告
        """
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"请基于以下研究数据生成结构化报告:\n{research_data}")
        ]
        
        response = await self.llm.ainvoke(messages)
        return response.content

