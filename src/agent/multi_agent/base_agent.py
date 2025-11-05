"""
多智能体系统 - 智能体基类

定义所有智能体的通用接口和行为
"""
from typing import Dict, List, Any, Optional, Type
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain.tools import BaseTool
from src.config import settings
from src.utils import app_logger


class AgentType(Enum):
    """智能体类型枚举"""
    COORDINATOR = "coordinator"  # 协调者
    ANALYST = "analyst"  # 分析师
    PLANNER = "planner"  # 规划师
    EXECUTOR = "executor"  # 执行者
    REVIEWER = "reviewer"  # 评审者
    RESEARCHER = "researcher"  # 研究员


class AgentStatus(Enum):
    """智能体状态枚举"""
    IDLE = "idle"  # 空闲
    BUSY = "busy"  # 忙碌
    ERROR = "error"  # 错误
    OFFLINE = "offline"  # 离线


@dataclass
class AgentCapability:
    """智能体能力定义"""
    name: str  # 能力名称
    description: str  # 能力描述
    required_tools: List[str] = field(default_factory=list)  # 需要的工具
    confidence: float = 1.0  # 能力置信度 0-1


@dataclass
class AgentMetadata:
    """智能体元数据"""
    agent_id: str
    agent_type: AgentType
    name: str
    description: str
    version: str = "1.0.0"
    capabilities: List[AgentCapability] = field(default_factory=list)
    status: AgentStatus = AgentStatus.IDLE
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class BaseAgent(ABC):
    """
    智能体基类

    所有专业智能体都应继承此类并实现抽象方法
    """

    def __init__(
        self,
        agent_id: str,
        agent_type: AgentType,
        name: str,
        description: str,
        llm: Optional[ChatOpenAI] = None,
        tools: Optional[List[BaseTool]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """
        初始化智能体

        Args:
            agent_id: 智能体唯一标识
            agent_type: 智能体类型
            name: 智能体名称
            description: 智能体描述
            llm: 大语言模型实例
            tools: 可用工具列表
            system_prompt: 系统提示词
            **kwargs: 其他参数
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.name = name
        self.description = description

        # 初始化 LLM
        self.llm = llm or ChatOpenAI(
            model=settings.model_name,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_api_base,
        )

        # 工具列表
        self.tools = tools or []

        # 系统提示词
        self.system_prompt = system_prompt or self._get_default_system_prompt()

        # 元数据
        self.metadata = AgentMetadata(
            agent_id=agent_id,
            agent_type=agent_type,
            name=name,
            description=description,
            capabilities=self._define_capabilities()
        )

        # 执行历史
        self.execution_history: List[Dict[str, Any]] = []

        # 打印智能体初始化信息
        app_logger.info(f"初始化智能体: {self.name} ({self.agent_type.value})")

        # 打印工具列表
        if self.tools:
            tool_names = [tool.name for tool in self.tools]
            app_logger.info(f"  ├─ 工具数量: {len(self.tools)}")
            app_logger.info(f"  └─ 工具列表: {', '.join(tool_names)}")
        else:
            app_logger.info(f"  └─ 无可用工具")

    @abstractmethod
    def _define_capabilities(self) -> List[AgentCapability]:
        """
        定义智能体能力

        子类必须实现此方法,返回智能体的能力列表

        Returns:
            List[AgentCapability]: 能力列表
        """
        pass

    @abstractmethod
    def _get_default_system_prompt(self) -> str:
        """
        获取默认系统提示词

        子类必须实现此方法,返回智能体的系统提示词

        Returns:
            str: 系统提示词
        """
        pass

    def _log_prompt(self, system_prompt: str, user_prompt: str) -> None:
        """
        记录 Prompt 日志

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
        """
        app_logger.info(f"\n{'='*80}\n[{self.name}] System Prompt:\n{'-'*80}\n{system_prompt}\n{'-'*80}")
        app_logger.info(f"\n[{self.name}] User Prompt:\n{'-'*80}\n{user_prompt}\n{'='*80}\n")

    def _log_response(self, response_content: str) -> None:
        """
        记录 Response 日志

        Args:
            response_content: LLM 响应内容
        """
        app_logger.info(f"\n{'='*80}\n[{self.name}] LLM Response:\n{'-'*80}\n{response_content}\n{'='*80}\n")

    @abstractmethod
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理任务的主方法

        子类必须实现此方法,定义智能体的核心处理逻辑

        Args:
            state: 当前状态

        Returns:
            Dict[str, Any]: 更新后的状态
        """
        pass

    async def analyze(self, input_data: Any) -> Dict[str, Any]:
        """
        分析输入数据

        Args:
            input_data: 输入数据

        Returns:
            Dict[str, Any]: 分析结果
        """
        app_logger.info(f"{self.name} 开始分析输入")

        try:
            # 构建消息
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=f"请分析以下内容:\n{input_data}")
            ]

            # 调用 LLM
            response = await self.llm.ainvoke(messages)

            result = {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "analysis": response.content,
                "success": True
            }

            app_logger.info(f"{self.name} 分析完成")
            return result

        except Exception as e:
            app_logger.error(f"{self.name} 分析失败: {str(e)}")
            return {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "error": str(e),
                "success": False
            }

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行具体任务

        Args:
            task: 任务描述

        Returns:
            Dict[str, Any]: 执行结果
        """
        app_logger.info(f"{self.name} 开始执行任务: {task.get('description', 'N/A')}")

        try:
            # 更新状态
            self.metadata.status = AgentStatus.BUSY

            # 记录执行历史
            execution_record = {
                "task": task,
                "timestamp": self._get_timestamp(),
                "status": "started"
            }
            self.execution_history.append(execution_record)

            # 调用 process 方法
            result = await self.process(task)

            # 更新执行记录
            execution_record["status"] = "completed"
            execution_record["result"] = result

            # 更新状态
            self.metadata.status = AgentStatus.IDLE

            app_logger.info(f"{self.name} 任务执行完成")
            return result

        except Exception as e:
            app_logger.error(f"{self.name} 任务执行失败: {str(e)}")
            self.metadata.status = AgentStatus.ERROR

            return {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "error": str(e),
                "success": False
            }

    async def validate(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证结果

        Args:
            result: 待验证的结果

        Returns:
            Dict[str, Any]: 验证结果
        """
        app_logger.info(f"{self.name} 开始验证结果")

        try:
            # 构建验证消息
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=f"请验证以下结果的正确性和完整性:\n{result}")
            ]

            # 调用 LLM
            response = await self.llm.ainvoke(messages)

            validation_result = {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "validation": response.content,
                "is_valid": True,  # 可以通过解析 response 来判断
                "success": True
            }

            app_logger.info(f"{self.name} 验证完成")
            return validation_result

        except Exception as e:
            app_logger.error(f"{self.name} 验证失败: {str(e)}")
            return {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "error": str(e),
                "success": False
            }

    def get_capabilities(self) -> List[AgentCapability]:
        """获取智能体能力列表"""
        return self.metadata.capabilities

    def get_status(self) -> AgentStatus:
        """获取智能体状态"""
        return self.metadata.status

    def get_metadata(self) -> AgentMetadata:
        """获取智能体元数据"""
        return self.metadata

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self.execution_history

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.agent_id} type={self.agent_type.value} status={self.metadata.status.value}>"

