"""
多智能体协作图 - LangGraph 实现

使用 LangGraph 实现多智能体协作的状态图和工作流
"""
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from src.utils import app_logger
from src.agent.memory import get_memory_saver

from .multi_agent_state import MultiAgentState, create_initial_state, mark_finished, mark_error
from .agent_coordinator import AgentCoordinator, agent_coordinator
from .agent_registry import AgentRegistry, agent_registry
from .agents import (
    AnalystAgent,
    PlannerAgent,
    ExecutorAgent,
    ReviewerAgent,
    ResearcherAgent,
)


def initialize_agents(registry: AgentRegistry) -> None:
    """
    初始化并注册所有智能体

    Args:
        registry: 智能体注册中心
    """
    app_logger.info("初始化多智能体系统")

    # 创建智能体实例
    analyst = AnalystAgent()
    planner = PlannerAgent()
    executor = ExecutorAgent()
    reviewer = ReviewerAgent()
    researcher = ResearcherAgent()

    # 注册智能体
    registry.register(analyst)
    registry.register(planner)
    registry.register(executor)
    registry.register(reviewer)
    registry.register(researcher)

    app_logger.info(f"✓ 已注册 {registry.get_agent_count()} 个智能体")


# 节点函数

async def coordinator_node(state: MultiAgentState) -> MultiAgentState:
    """
    协调器节点

    负责任务分析、智能体调度和流程控制
    """
    app_logger.info("执行协调器节点")

    try:
        # 使用协调器处理任务
        coordinator = agent_coordinator
        updated_state = await coordinator.coordinate(state)
        return updated_state

    except Exception as e:
        app_logger.error(f"协调器节点执行失败: {str(e)}")
        return mark_error(state, str(e))


async def analyst_node(state: MultiAgentState) -> MultiAgentState:
    """分析师节点"""
    app_logger.info("执行分析师节点")

    try:
        analyst = agent_registry.find_best_agent(agent_type=AnalystAgent.agent_type)
        if not analyst:
            raise ValueError("未找到分析师智能体")

        result = await analyst.execute(state)
        state["agent_results"][analyst.agent_id] = result
        state["current_agent"] = analyst.agent_id

        return state

    except Exception as e:
        app_logger.error(f"分析师节点执行失败: {str(e)}")
        return mark_error(state, str(e))


async def planner_node(state: MultiAgentState) -> MultiAgentState:
    """规划师节点"""
    app_logger.info("执行规划师节点")

    try:
        planner = agent_registry.find_best_agent(agent_type=PlannerAgent.agent_type)
        if not planner:
            raise ValueError("未找到规划师智能体")

        result = await planner.execute(state)
        state["agent_results"][planner.agent_id] = result
        state["current_agent"] = planner.agent_id
        state["task_plan"] = result.get("plan", [])

        return state

    except Exception as e:
        app_logger.error(f"规划师节点执行失败: {str(e)}")
        return mark_error(state, str(e))


async def executor_node(state: MultiAgentState) -> MultiAgentState:
    """执行者节点"""
    app_logger.info("执行执行者节点")

    try:
        executor = agent_registry.find_best_agent(agent_type=ExecutorAgent.agent_type)
        if not executor:
            raise ValueError("未找到执行者智能体")

        result = await executor.execute(state)
        state["agent_results"][executor.agent_id] = result
        state["current_agent"] = executor.agent_id

        return state

    except Exception as e:
        app_logger.error(f"执行者节点执行失败: {str(e)}")
        return mark_error(state, str(e))


async def reviewer_node(state: MultiAgentState) -> MultiAgentState:
    """评审者节点"""
    app_logger.info("执行评审者节点")

    try:
        reviewer = agent_registry.find_best_agent(agent_type=ReviewerAgent.agent_type)
        if not reviewer:
            raise ValueError("未找到评审者智能体")

        result = await reviewer.execute(state)
        state["agent_results"][reviewer.agent_id] = result
        state["current_agent"] = reviewer.agent_id
        state["review_result"] = result
        state["review_passed"] = result.get("passed", False)

        return state

    except Exception as e:
        app_logger.error(f"评审者节点执行失败: {str(e)}")
        return mark_error(state, str(e))


async def researcher_node(state: MultiAgentState) -> MultiAgentState:
    """研究员节点"""
    app_logger.info("执行研究员节点")

    try:
        researcher = agent_registry.find_best_agent(agent_type=ResearcherAgent.agent_type)
        if not researcher:
            raise ValueError("未找到研究员智能体")

        result = await researcher.execute(state)
        state["agent_results"][researcher.agent_id] = result
        state["current_agent"] = researcher.agent_id

        return state

    except Exception as e:
        app_logger.error(f"研究员节点执行失败: {str(e)}")
        return mark_error(state, str(e))


# 路由函数

def route_next_agent(state: MultiAgentState) -> Literal["analyst", "planner", "executor", "reviewer", "researcher", "end"]:
    """
    路由到下一个智能体

    根据协作模式和当前状态决定下一个执行的智能体
    """
    # 检查是否完成
    if state.get("is_finished", False):
        return "end"

    # 检查是否有错误
    if state.get("error"):
        return "end"

    # 检查迭代次数
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 10)
    if iteration >= max_iterations:
        app_logger.warning(f"达到最大迭代次数 {max_iterations}")
        return "end"

    # 获取协作模式
    mode = state.get("coordination_mode", "sequential")
    current_agent = state.get("current_agent")

    # 顺序模式
    if mode == "sequential":
        if not current_agent:
            return "analyst"
        elif "analyst" in current_agent:
            return "planner"
        elif "planner" in current_agent:
            return "executor"
        elif "executor" in current_agent:
            return "reviewer"
        else:
            return "end"

    # 反馈模式
    elif mode == "feedback":
        if not current_agent:
            return "executor"
        elif "executor" in current_agent:
            return "reviewer"
        elif "reviewer" in current_agent:
            # 检查是否通过评审
            if state.get("review_passed", False):
                return "end"
            else:
                # 检查反馈轮次
                feedback_round = state.get("feedback_round", 0)
                max_rounds = state.get("max_feedback_rounds", 3)
                if feedback_round >= max_rounds:
                    app_logger.warning(f"达到最大反馈轮次 {max_rounds}")
                    return "end"
                return "executor"
        else:
            return "end"

    # 默认结束
    return "end"


def should_continue(state: MultiAgentState) -> bool:
    """判断是否应该继续执行"""
    return not state.get("is_finished", False) and not state.get("error")


# 创建多智能体图

def create_multi_agent_graph(enable_memory: bool = True):
    """
    创建多智能体协作图

    Args:
        enable_memory: 是否启用记忆功能

    Returns:
        编译后的图实例
    """
    app_logger.info(f"创建多智能体协作图 (记忆功能: {'启用' if enable_memory else '禁用'})")

    # 初始化智能体
    initialize_agents(agent_registry)

    # 创建状态图
    workflow = StateGraph(MultiAgentState)

    # 只添加协调器节点 - 协调器内部会执行所有智能体
    workflow.add_node("coordinator", coordinator_node)

    # 设置入口点
    workflow.set_entry_point("coordinator")

    # 协调器执行完直接结束
    workflow.add_edge("coordinator", END)

    # 编译图
    if enable_memory:
        memory_saver = get_memory_saver()
        app = workflow.compile(checkpointer=memory_saver)
        app_logger.info("多智能体协作图创建完成 (已集成 InMemorySaver)")
    else:
        app = workflow.compile()
        app_logger.info("多智能体协作图创建完成 (未启用记忆功能)")

    return app


# 创建全局多智能体图实例
multi_agent_graph = create_multi_agent_graph(enable_memory=True)

