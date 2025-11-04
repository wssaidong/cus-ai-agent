"""
评审者智能体 (ReviewerAgent)

职责: 结果验证、质量检查、改进建议
"""
from typing import Dict, List, Any
from langchain_core.messages import HumanMessage, SystemMessage
from ..base_agent import BaseAgent, AgentType, AgentCapability
from src.utils import app_logger


class ReviewerAgent(BaseAgent):
    """
    评审者智能体
    
    能力:
    - 结果验证
    - 质量评估
    - 错误检测
    - 改进建议
    """
    
    def __init__(self, agent_id: str = "reviewer_001", **kwargs):
        """初始化评审者智能体"""
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.REVIEWER,
            name="评审者",
            description="负责结果验证、质量检查和改进建议",
            **kwargs
        )
    
    def _define_capabilities(self) -> List[AgentCapability]:
        """定义评审者能力"""
        return [
            AgentCapability(
                name="结果验证",
                description="验证执行结果的正确性",
                confidence=0.9
            ),
            AgentCapability(
                name="质量评估",
                description="评估结果的质量和完整性",
                confidence=0.85
            ),
            AgentCapability(
                name="错误检测",
                description="检测结果中的错误和问题",
                confidence=0.85
            ),
            AgentCapability(
                name="改进建议",
                description="提供改进建议和优化方案",
                confidence=0.8
            ),
        ]
    
    def _get_default_system_prompt(self) -> str:
        """获取评审者系统提示词"""
        return """你是一个专业的评审者智能体。

你的职责:
1. 验证执行结果的正确性
2. 评估结果的质量和完整性
3. 检测潜在的错误和问题
4. 提供具体的改进建议

评审标准:
- 正确性: 结果是否正确
- 完整性: 是否完整满足需求
- 质量: 结果的质量如何
- 可用性: 结果是否可用

输出格式:
请以 JSON 格式输出评审结果,包含以下字段:
{
    "passed": true/false,
    "score": 85,
    "correctness": "正确性评估",
    "completeness": "完整性评估",
    "quality": "质量评估",
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"],
    "summary": "评审总结"
}
"""
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理评审任务
        
        Args:
            state: 当前状态
            
        Returns:
            Dict[str, Any]: 评审结果
        """
        try:
            app_logger.info(f"{self.name} 开始评审结果")
            
            # 获取任务信息
            task = state.get("task", {})
            task_description = task.get("description", "")
            requirements = task.get("requirements", [])
            
            # 获取执行结果
            agent_results = state.get("agent_results", {})
            executor_result = None
            for agent_id, result in agent_results.items():
                if "executor" in agent_id:
                    executor_result = result
                    break
            
            if not executor_result:
                app_logger.warning("未找到执行结果,无法评审")
                return {
                    "agent_id": self.agent_id,
                    "agent_type": self.agent_type.value,
                    "agent_name": self.name,
                    "passed": False,
                    "error": "未找到执行结果",
                    "success": False
                }
            
            # 构建评审提示
            review_prompt = f"""
请评审以下执行结果:

原始任务: {task_description}

需求要求:
{chr(10).join([f"- {req}" for req in requirements]) if requirements else "无明确要求"}

执行结果:
{executor_result.get('output', executor_result)}

请评估:
1. 正确性: 结果是否正确完成了任务
2. 完整性: 是否满足所有需求
3. 质量: 结果的质量如何
4. 问题: 存在哪些问题
5. 建议: 如何改进
"""
            
            # 调用 LLM 进行评审
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=review_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # 解析结果
            import json
            try:
                review_result = json.loads(response.content)
            except json.JSONDecodeError:
                # 如果不是 JSON,尝试从文本中提取信息
                review_result = {
                    "passed": "通过" in response.content or "成功" in response.content,
                    "summary": response.content,
                    "raw_output": True
                }
            
            # 构建返回结果
            result = {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "agent_name": self.name,
                "passed": review_result.get("passed", False),
                "score": review_result.get("score", 0),
                "correctness": review_result.get("correctness", ""),
                "completeness": review_result.get("completeness", ""),
                "quality": review_result.get("quality", ""),
                "issues": review_result.get("issues", []),
                "suggestions": review_result.get("suggestions", []),
                "summary": review_result.get("summary", ""),
                "success": True,
                "output": response.content
            }
            
            app_logger.info(f"{self.name} 评审完成: {'通过' if result['passed'] else '不通过'}")
            return result
            
        except Exception as e:
            app_logger.error(f"{self.name} 评审失败: {str(e)}")
            return {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "agent_name": self.name,
                "error": str(e),
                "passed": False,
                "success": False
            }
    
    async def review_quality(self, result: Any) -> Dict[str, Any]:
        """
        评审质量
        
        Args:
            result: 待评审的结果
            
        Returns:
            Dict[str, Any]: 质量评审结果
        """
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"请评审以下结果的质量:\n{result}")
        ]
        
        response = await self.llm.ainvoke(messages)
        
        import json
        try:
            review = json.loads(response.content)
            return review
        except:
            return {
                "quality": response.content,
                "agent_id": self.agent_id
            }
    
    async def suggest_improvements(self, result: Any) -> List[str]:
        """
        提供改进建议
        
        Args:
            result: 待改进的结果
            
        Returns:
            List[str]: 改进建议列表
        """
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"请为以下结果提供改进建议:\n{result}")
        ]
        
        response = await self.llm.ainvoke(messages)
        
        import json
        try:
            suggestions = json.loads(response.content)
            return suggestions.get("suggestions", [])
        except:
            return [response.content]

