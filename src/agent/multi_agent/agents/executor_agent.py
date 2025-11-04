"""
执行者智能体 (ExecutorAgent)

职责: 具体任务执行、工具调用、结果生成
"""
from typing import Dict, List, Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.tools import BaseTool
from ..base_agent import BaseAgent, AgentType, AgentCapability
from src.utils import app_logger
from src.tools import get_available_tools


class ExecutorAgent(BaseAgent):
    """
    执行者智能体
    
    能力:
    - 工具调用
    - 代码执行
    - API 调用
    - 文件操作
    """
    
    def __init__(
        self,
        agent_id: str = "executor_001",
        tools: Optional[List[BaseTool]] = None,
        **kwargs
    ):
        """初始化执行者智能体"""
        # 如果没有提供工具,使用所有可用工具
        if tools is None:
            tools = get_available_tools()
        
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.EXECUTOR,
            name="执行者",
            description="负责具体任务执行、工具调用和结果生成",
            tools=tools,
            **kwargs
        )
    
    def _define_capabilities(self) -> List[AgentCapability]:
        """定义执行者能力"""
        return [
            AgentCapability(
                name="工具调用",
                description="调用各种工具完成任务",
                required_tools=["*"],
                confidence=0.9
            ),
            AgentCapability(
                name="任务执行",
                description="执行具体的任务步骤",
                confidence=0.85
            ),
            AgentCapability(
                name="结果生成",
                description="生成任务执行结果",
                confidence=0.85
            ),
            AgentCapability(
                name="错误处理",
                description="处理执行过程中的错误",
                confidence=0.8
            ),
        ]
    
    def _get_default_system_prompt(self) -> str:
        """获取执行者系统提示词"""
        tools_desc = "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])
        
        return f"""你是一个专业的执行者智能体。

你的职责:
1. 执行具体的任务步骤
2. 调用合适的工具完成任务
3. 生成清晰的执行结果
4. 处理执行过程中的错误

可用工具:
{tools_desc}

执行原则:
- 准确性: 严格按照计划执行
- 效率性: 选择最合适的工具
- 完整性: 确保任务完整执行
- 可靠性: 处理可能的错误

输出格式:
请以 JSON 格式输出执行结果,包含以下字段:
{{
    "executed_steps": ["步骤1", "步骤2"],
    "tools_used": ["工具1", "工具2"],
    "results": {{"key": "value"}},
    "status": "success/failed",
    "output": "执行结果描述"
}}
"""
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理执行任务
        
        Args:
            state: 当前状态
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            app_logger.info(f"{self.name} 开始执行任务")
            
            # 获取任务信息
            task = state.get("task", {})
            task_description = task.get("description", "")
            
            # 获取执行计划(如果有)
            task_plan = state.get("task_plan", [])
            
            # 构建执行提示
            execution_prompt = f"""
请执行以下任务:

任务描述: {task_description}
"""
            
            if task_plan:
                execution_prompt += f"\n执行计划:\n"
                for i, step in enumerate(task_plan, 1):
                    execution_prompt += f"{i}. {step.get('description', step)}\n"
            
            execution_prompt += """
请:
1. 按照计划执行每个步骤
2. 选择合适的工具(如果需要)
3. 记录执行过程和结果
4. 处理可能的错误
"""
            
            # 调用 LLM 执行任务
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=execution_prompt)
            ]
            
            # 如果有工具,使用工具增强的 LLM
            if self.tools:
                llm_with_tools = self.llm.bind_tools(self.tools)
                response = await llm_with_tools.ainvoke(messages)
            else:
                response = await self.llm.ainvoke(messages)
            
            # 解析结果
            import json
            try:
                execution_result = json.loads(response.content)
            except json.JSONDecodeError:
                execution_result = {
                    "output": response.content,
                    "status": "success",
                    "raw_output": True
                }
            
            # 构建返回结果
            result = {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "agent_name": self.name,
                "executed_steps": execution_result.get("executed_steps", []),
                "tools_used": execution_result.get("tools_used", []),
                "results": execution_result.get("results", {}),
                "status": execution_result.get("status", "success"),
                "success": True,
                "output": response.content
            }
            
            app_logger.info(f"{self.name} 执行完成")
            return result
            
        except Exception as e:
            app_logger.error(f"{self.name} 执行失败: {str(e)}")
            return {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "agent_name": self.name,
                "error": str(e),
                "status": "failed",
                "success": False
            }
    
    async def execute_with_tools(
        self,
        task: str,
        tools: Optional[List[BaseTool]] = None
    ) -> Dict[str, Any]:
        """
        使用工具执行任务
        
        Args:
            task: 任务描述
            tools: 可用工具列表
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        tools_to_use = tools or self.tools
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"请使用可用工具执行以下任务:\n{task}")
        ]
        
        if tools_to_use:
            llm_with_tools = self.llm.bind_tools(tools_to_use)
            response = await llm_with_tools.ainvoke(messages)
        else:
            response = await self.llm.ainvoke(messages)
        
        return {
            "task": task,
            "result": response.content,
            "agent_id": self.agent_id
        }

