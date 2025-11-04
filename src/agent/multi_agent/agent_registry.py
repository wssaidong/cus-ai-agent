"""
多智能体系统 - 智能体注册中心

管理所有智能体的注册、发现和生命周期
"""
from typing import Dict, List, Optional, Type
from .base_agent import BaseAgent, AgentType, AgentStatus, AgentCapability
from src.utils import app_logger


class AgentRegistry:
    """
    智能体注册中心
    
    功能:
    - 智能体注册与注销
    - 智能体查询与发现
    - 智能体状态管理
    - 智能体能力匹配
    """
    
    def __init__(self):
        """初始化注册中心"""
        # 智能体存储: agent_id -> BaseAgent
        self._agents: Dict[str, BaseAgent] = {}
        
        # 类型索引: agent_type -> List[agent_id]
        self._type_index: Dict[AgentType, List[str]] = {
            agent_type: [] for agent_type in AgentType
        }
        
        # 能力索引: capability_name -> List[agent_id]
        self._capability_index: Dict[str, List[str]] = {}
        
        app_logger.info("智能体注册中心初始化完成")
    
    def register(self, agent: BaseAgent) -> bool:
        """
        注册智能体
        
        Args:
            agent: 智能体实例
            
        Returns:
            bool: 注册是否成功
        """
        try:
            agent_id = agent.agent_id
            
            # 检查是否已注册
            if agent_id in self._agents:
                app_logger.warning(f"智能体 {agent_id} 已注册,将覆盖")
            
            # 注册智能体
            self._agents[agent_id] = agent
            
            # 更新类型索引
            if agent_id not in self._type_index[agent.agent_type]:
                self._type_index[agent.agent_type].append(agent_id)
            
            # 更新能力索引
            for capability in agent.get_capabilities():
                if capability.name not in self._capability_index:
                    self._capability_index[capability.name] = []
                if agent_id not in self._capability_index[capability.name]:
                    self._capability_index[capability.name].append(agent_id)
            
            app_logger.info(f"✓ 智能体注册成功: {agent.name} ({agent_id})")
            return True
            
        except Exception as e:
            app_logger.error(f"✗ 智能体注册失败: {str(e)}")
            return False
    
    def unregister(self, agent_id: str) -> bool:
        """
        注销智能体
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            bool: 注销是否成功
        """
        try:
            if agent_id not in self._agents:
                app_logger.warning(f"智能体 {agent_id} 未注册")
                return False
            
            agent = self._agents[agent_id]
            
            # 从类型索引中移除
            if agent_id in self._type_index[agent.agent_type]:
                self._type_index[agent.agent_type].remove(agent_id)
            
            # 从能力索引中移除
            for capability in agent.get_capabilities():
                if capability.name in self._capability_index:
                    if agent_id in self._capability_index[capability.name]:
                        self._capability_index[capability.name].remove(agent_id)
            
            # 移除智能体
            del self._agents[agent_id]
            
            app_logger.info(f"✓ 智能体注销成功: {agent_id}")
            return True
            
        except Exception as e:
            app_logger.error(f"✗ 智能体注销失败: {str(e)}")
            return False
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """
        获取智能体
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            Optional[BaseAgent]: 智能体实例,不存在则返回 None
        """
        return self._agents.get(agent_id)
    
    def get_agents_by_type(self, agent_type: AgentType) -> List[BaseAgent]:
        """
        根据类型获取智能体列表
        
        Args:
            agent_type: 智能体类型
            
        Returns:
            List[BaseAgent]: 智能体列表
        """
        agent_ids = self._type_index.get(agent_type, [])
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]
    
    def get_agents_by_capability(self, capability_name: str) -> List[BaseAgent]:
        """
        根据能力获取智能体列表
        
        Args:
            capability_name: 能力名称
            
        Returns:
            List[BaseAgent]: 智能体列表
        """
        agent_ids = self._capability_index.get(capability_name, [])
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]
    
    def get_available_agents(self) -> List[BaseAgent]:
        """
        获取所有可用(非离线)的智能体
        
        Returns:
            List[BaseAgent]: 可用智能体列表
        """
        return [
            agent for agent in self._agents.values()
            if agent.get_status() != AgentStatus.OFFLINE
        ]
    
    def get_idle_agents(self) -> List[BaseAgent]:
        """
        获取所有空闲的智能体
        
        Returns:
            List[BaseAgent]: 空闲智能体列表
        """
        return [
            agent for agent in self._agents.values()
            if agent.get_status() == AgentStatus.IDLE
        ]
    
    def find_best_agent(
        self,
        agent_type: Optional[AgentType] = None,
        required_capabilities: Optional[List[str]] = None,
        prefer_idle: bool = True
    ) -> Optional[BaseAgent]:
        """
        查找最佳智能体
        
        Args:
            agent_type: 智能体类型(可选)
            required_capabilities: 需要的能力列表(可选)
            prefer_idle: 是否优先选择空闲智能体
            
        Returns:
            Optional[BaseAgent]: 最佳智能体,未找到则返回 None
        """
        candidates = list(self._agents.values())
        
        # 按类型过滤
        if agent_type:
            candidates = [a for a in candidates if a.agent_type == agent_type]
        
        # 按能力过滤
        if required_capabilities:
            candidates = [
                a for a in candidates
                if all(
                    any(cap.name == req_cap for cap in a.get_capabilities())
                    for req_cap in required_capabilities
                )
            ]
        
        # 过滤掉离线的
        candidates = [a for a in candidates if a.get_status() != AgentStatus.OFFLINE]
        
        if not candidates:
            return None
        
        # 优先选择空闲的
        if prefer_idle:
            idle_candidates = [a for a in candidates if a.get_status() == AgentStatus.IDLE]
            if idle_candidates:
                return idle_candidates[0]
        
        return candidates[0]
    
    def get_all_agents(self) -> List[BaseAgent]:
        """
        获取所有智能体
        
        Returns:
            List[BaseAgent]: 所有智能体列表
        """
        return list(self._agents.values())
    
    def get_agent_count(self) -> int:
        """
        获取智能体总数
        
        Returns:
            int: 智能体总数
        """
        return len(self._agents)
    
    def get_statistics(self) -> Dict[str, any]:
        """
        获取注册中心统计信息
        
        Returns:
            Dict[str, any]: 统计信息
        """
        stats = {
            "total_agents": len(self._agents),
            "agents_by_type": {},
            "agents_by_status": {
                "idle": 0,
                "busy": 0,
                "error": 0,
                "offline": 0
            },
            "total_capabilities": len(self._capability_index),
        }
        
        # 按类型统计
        for agent_type in AgentType:
            stats["agents_by_type"][agent_type.value] = len(self._type_index[agent_type])
        
        # 按状态统计
        for agent in self._agents.values():
            status = agent.get_status()
            if status == AgentStatus.IDLE:
                stats["agents_by_status"]["idle"] += 1
            elif status == AgentStatus.BUSY:
                stats["agents_by_status"]["busy"] += 1
            elif status == AgentStatus.ERROR:
                stats["agents_by_status"]["error"] += 1
            elif status == AgentStatus.OFFLINE:
                stats["agents_by_status"]["offline"] += 1
        
        return stats
    
    def clear(self):
        """清空所有注册的智能体"""
        self._agents.clear()
        for agent_type in AgentType:
            self._type_index[agent_type].clear()
        self._capability_index.clear()
        app_logger.info("智能体注册中心已清空")


# 全局注册中心实例
agent_registry = AgentRegistry()

