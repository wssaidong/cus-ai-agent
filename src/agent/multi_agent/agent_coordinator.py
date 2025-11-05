"""
多智能体系统 - 协调器

负责多智能体间的协调、任务分配和结果聚合
"""
from typing import Dict, List, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from .base_agent import BaseAgent, AgentType
from .agent_registry import AgentRegistry, agent_registry
from .multi_agent_state import MultiAgentState, update_agent_result, mark_finished, mark_error
from src.utils import app_logger


class AgentCoordinator:
    """
    智能体协调器

    功能:
    - 任务分析与分解
    - 智能体选择与调度
    - 执行流程控制
    - 结果聚合与优化
    """

    def __init__(self, registry: Optional[AgentRegistry] = None):
        """
        初始化协调器

        Args:
            registry: 智能体注册中心,默认使用全局实例
        """
        self.registry = registry or agent_registry
        app_logger.info("智能体协调器初始化完成")

    async def coordinate(self, state: MultiAgentState) -> MultiAgentState:
        """
        协调多智能体执行任务

        Args:
            state: 当前状态

        Returns:
            MultiAgentState: 更新后的状态
        """
        try:
            app_logger.info(f"开始协调任务: {state['task'].get('description', 'N/A')}")

            # 获取协作模式
            mode = state.get("coordination_mode", "sequential")

            # 根据模式执行
            if mode == "sequential":
                return await self._coordinate_sequential(state)
            elif mode == "parallel":
                return await self._coordinate_parallel(state)
            elif mode == "hierarchical":
                return await self._coordinate_hierarchical(state)
            elif mode == "feedback":
                return await self._coordinate_feedback(state)
            else:
                app_logger.warning(f"未知的协作模式: {mode}, 使用顺序模式")
                return await self._coordinate_sequential(state)

        except Exception as e:
            app_logger.error(f"协调任务失败: {str(e)}")
            return mark_error(state, str(e))

    async def _coordinate_sequential(self, state: MultiAgentState) -> MultiAgentState:
        """
        顺序协作模式

        智能体按顺序依次执行: Analyst -> Planner -> Executor -> Reviewer

        Args:
            state: 当前状态

        Returns:
            MultiAgentState: 更新后的状态
        """
        app_logger.info("使用顺序协作模式")

        # 定义执行顺序
        agent_sequence = [
            AgentType.ANALYST,
            AgentType.PLANNER,
            AgentType.EXECUTOR,
            AgentType.REVIEWER,
        ]

        # 依次执行
        for agent_type in agent_sequence:
            # 查找智能体
            agent = self.registry.find_best_agent(agent_type=agent_type)

            if not agent:
                app_logger.warning(f"未找到类型为 {agent_type.value} 的智能体,跳过")
                continue

            # 更新当前智能体
            state["current_agent"] = agent.agent_id

            # 执行任务
            app_logger.info(f"执行智能体: {agent.name} ({agent_type.value})")
            result = await agent.execute(state)

            # 更新结果
            state = update_agent_result(state, agent.agent_id, result)

            # 检查是否成功
            if not result.get("success", False):
                app_logger.error(f"智能体 {agent.name} 执行失败")
                return mark_error(state, f"智能体 {agent.name} 执行失败")

        # 聚合结果
        final_result = self._aggregate_results(state)
        return mark_finished(state, final_result)

    async def _coordinate_parallel(self, state: MultiAgentState) -> MultiAgentState:
        """
        并行协作模式

        多个智能体同时执行不同的子任务

        Args:
            state: 当前状态

        Returns:
            MultiAgentState: 更新后的状态
        """
        app_logger.info("使用并行协作模式")

        import asyncio

        # 获取任务计划
        task_plan = state.get("task_plan", [])

        if not task_plan:
            app_logger.warning("任务计划为空,无法并行执行")
            return mark_error(state, "任务计划为空")

        # 创建并行任务
        tasks = []
        agents = []

        for subtask in task_plan:
            # 根据子任务类型选择智能体
            agent_type_str = subtask.get("agent_type", "executor")
            agent_type = AgentType(agent_type_str)

            agent = self.registry.find_best_agent(agent_type=agent_type)
            if agent:
                agents.append(agent)
                tasks.append(agent.execute(subtask))
            else:
                app_logger.warning(f"未找到类型为 {agent_type.value} 的智能体")

        # 并行执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 更新结果
        for agent, result in zip(agents, results):
            if isinstance(result, Exception):
                app_logger.error(f"智能体 {agent.name} 执行异常: {str(result)}")
                state = update_agent_result(state, agent.agent_id, {
                    "success": False,
                    "error": str(result)
                })
            else:
                state = update_agent_result(state, agent.agent_id, result)

        # 聚合结果
        final_result = self._aggregate_results(state)
        return mark_finished(state, final_result)

    async def _coordinate_hierarchical(self, state: MultiAgentState) -> MultiAgentState:
        """
        层级协作模式

        协调者分配任务给下级智能体

        Args:
            state: 当前状态

        Returns:
            MultiAgentState: 更新后的状态
        """
        app_logger.info("使用层级协作模式")

        # 1. 使用 Planner 制定计划
        planner = self.registry.find_best_agent(agent_type=AgentType.PLANNER)
        if planner:
            plan_result = await planner.execute(state)
            state = update_agent_result(state, planner.agent_id, plan_result)
            state["task_plan"] = plan_result.get("plan", [])

        # 2. 使用 Executor 执行计划
        executor = self.registry.find_best_agent(agent_type=AgentType.EXECUTOR)
        if executor:
            exec_result = await executor.execute(state)
            state = update_agent_result(state, executor.agent_id, exec_result)

        # 3. 使用 Reviewer 评审结果
        reviewer = self.registry.find_best_agent(agent_type=AgentType.REVIEWER)
        if reviewer:
            review_result = await reviewer.execute(state)
            state = update_agent_result(state, reviewer.agent_id, review_result)
            state["review_result"] = review_result
            state["review_passed"] = review_result.get("passed", False)

        # 聚合结果
        final_result = self._aggregate_results(state)
        return mark_finished(state, final_result)

    async def _coordinate_feedback(self, state: MultiAgentState) -> MultiAgentState:
        """
        反馈协作模式

        智能体之间形成反馈循环,不断优化结果

        Args:
            state: 当前状态

        Returns:
            MultiAgentState: 更新后的状态
        """
        app_logger.info("使用反馈协作模式")

        max_rounds = state.get("max_feedback_rounds", 3)

        for round_num in range(max_rounds):
            state["feedback_round"] = round_num + 1
            app_logger.info(f"反馈轮次: {round_num + 1}/{max_rounds}")

            # 1. Executor 执行
            executor = self.registry.find_best_agent(agent_type=AgentType.EXECUTOR)
            if executor:
                exec_result = await executor.execute(state)
                state = update_agent_result(state, executor.agent_id, exec_result)

            # 2. Reviewer 评审
            reviewer = self.registry.find_best_agent(agent_type=AgentType.REVIEWER)
            if reviewer:
                review_result = await reviewer.execute(state)
                state = update_agent_result(state, reviewer.agent_id, review_result)

                # 检查是否通过
                if review_result.get("passed", False):
                    app_logger.info("评审通过,结束反馈循环")
                    break

                # 获取改进建议
                suggestions = review_result.get("suggestions", [])
                state["improvement_suggestions"] = suggestions
                app_logger.info(f"评审未通过,改进建议: {suggestions}")

        # 聚合结果
        final_result = self._aggregate_results(state)
        return mark_finished(state, final_result)

    def _aggregate_results(self, state: MultiAgentState) -> Dict[str, Any]:
        """
        聚合各智能体的结果，生成符合 OpenAI 格式的友好答案

        Args:
            state: 当前状态

        Returns:
            Dict[str, Any]: 聚合后的最终结果
        """
        import json
        import re

        agent_results = state.get("agent_results", {})
        task = state.get("task", {})

        # 提取任务描述
        if isinstance(task, dict):
            task_description = task.get("description", "")
        else:
            task_description = str(task)

        # 提取各智能体的关键信息
        aggregated = {
            "task": task,
            "coordination_mode": state.get("coordination_mode"),
            "agents_involved": list(agent_results.keys()),
            "results": {},
            "summary": "",
            "output": "",  # 用于 OpenAI 兼容接口
        }

        # 整理各智能体结果
        for agent_id, result in agent_results.items():
            aggregated["results"][agent_id] = result

        # 生成友好的最终答案
        if agent_results:
            # 辅助函数：清理输出内容
            def clean_output(output_str: str) -> str:
                """清理输出内容，移除智能体标记和多余的格式"""
                if not output_str:
                    return ""

                # 移除智能体标记（如 [分析师]:、[规划师]:、[执行者]:、[评审者]: 等）
                cleaned = re.sub(r'\[[\u4e00-\u9fa5]+\]:\s*', '', output_str)

                # 移除 JSON 标记（如果有）
                cleaned = re.sub(r'```json\s*', '', cleaned)
                cleaned = re.sub(r'```\s*', '', cleaned)

                # 移除多余的空行
                cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

                # 移除开头和结尾的空白
                cleaned = cleaned.strip()

                return cleaned

            # 收集各智能体的输出
            analyst_content = None
            planner_content = None
            executor_content = None
            reviewer_content = None
            researcher_content = None

            for agent_id, result in agent_results.items():
                raw_output = result.get("output", "")
                cleaned_content = clean_output(raw_output)

                if "analyst" in agent_id.lower():
                    analyst_content = cleaned_content
                elif "planner" in agent_id.lower():
                    planner_content = cleaned_content
                elif "executor" in agent_id.lower():
                    executor_content = cleaned_content
                elif "reviewer" in agent_id.lower():
                    reviewer_content = cleaned_content
                elif "researcher" in agent_id.lower():
                    researcher_content = cleaned_content

            # 构建最终答案 - 优先级：执行结果 > 分析结果 > 研究结果 > 规划结果
            final_answer = ""

            if executor_content:
                # 如果有执行结果，这是最重要的
                final_answer = executor_content
            elif analyst_content:
                # 如果只有分析结果
                final_answer = analyst_content
            elif researcher_content:
                # 如果有研究结果
                final_answer = researcher_content
            elif planner_content:
                # 如果只有规划结果
                final_answer = planner_content
            else:
                # 使用最后一个智能体的输出
                last_result = list(agent_results.values())[-1]
                last_output = last_result.get("output", "")
                final_answer = clean_output(last_output)

            # 如果答案仍然为空，生成默认答案
            if not final_answer or final_answer.strip() == "":
                final_answer = f"任务已完成处理，涉及 {len(agent_results)} 个智能体协作。"

            aggregated["summary"] = final_answer
            aggregated["output"] = final_answer

        return aggregated

    def get_registry(self) -> AgentRegistry:
        """获取注册中心"""
        return self.registry


# 全局协调器实例
agent_coordinator = AgentCoordinator()

