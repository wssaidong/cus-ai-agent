"""
AnalysisAgent - 分析智能体

专门负责数据分析、推理、计算等复杂任务
"""
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain.tools import BaseTool
from src.config import settings
from src.utils import app_logger
from src.agent.multi_agent.chat_state import ChatState


class AnalysisAgent:
    """
    分析智能体 - Worker Agent

    职责：
    1. 接收 Supervisor 的分析任务指令
    2. 调用分析相关工具（计算器、数据处理等）
    3. 进行推理和分析
    4. 生成分析报告

    专长：
    - 数据分析
    - 逻辑推理
    - 计算任务
    - 对比分析
    - 趋势预测
    """

    def __init__(self, llm: ChatOpenAI = None, tools: List[BaseTool] = None):
        """初始化分析智能体"""
        self.name = "AnalysisAgent"
        self.llm = llm or ChatOpenAI(
            model=settings.model_name,
            temperature=0.5,  # 中等温度，平衡创造性和准确性
            max_tokens=settings.max_tokens,
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_api_base,
            streaming=True,  # 启用流式输出
        )

        # 过滤出分析相关的工具
        self.tools = self._filter_analysis_tools(tools or [])
        self.tool_map = {tool.name: tool for tool in self.tools}

        # 如果有工具，绑定到 LLM
        if self.tools:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
        else:
            self.llm_with_tools = self.llm

        self.system_prompt = self._get_system_prompt()

        app_logger.info(f"[{self.name}] 初始化完成，可用工具: {list(self.tool_map.keys())}")

    def _filter_analysis_tools(self, tools: List[BaseTool]) -> List[BaseTool]:
        """过滤出分析相关的工具"""
        analysis_keywords = ["calculate", "compute", "analyze", "process", "compare", "evaluate"]
        filtered_tools = []

        for tool in tools:
            tool_name_lower = tool.name.lower()
            if any(keyword in tool_name_lower for keyword in analysis_keywords):
                filtered_tools.append(tool)

        # 如果没有找到分析工具，返回所有工具（向后兼容）
        if not filtered_tools:
            app_logger.warning(f"[{self.name}] 未找到分析相关工具，使用所有工具")
            return tools

        return filtered_tools

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        tool_descriptions = ""
        if self.tools:
            tool_descriptions = "\n【可用工具】\n"
            for tool in self.tools:
                tool_descriptions += f"- {tool.name}: {tool.description}\n"

        return f"""你是一个专业的分析智能体（AnalysisAgent），专门负责数据分析、推理和计算任务。

⚠️ **重要约束：必须使用中文回答用户的所有问题！**

【核心职责】
1. 理解 Supervisor 给出的分析任务
2. 调用分析工具进行计算和处理
3. 进行逻辑推理和数据分析
4. 生成清晰的分析报告

{tool_descriptions}

【工作流程】
1. 仔细阅读分析任务指令
2. 确定分析方法和策略
3. 调用合适的分析工具
4. 整理和解释分析结果
5. 生成结构化的分析报告

【分析能力】
1. **数据分析**: 处理和分析数据，发现规律
2. **逻辑推理**: 基于已知信息进行推理
3. **对比分析**: 比较不同方案、选项的优劣
4. **计算任务**: 执行数学计算和公式求解
5. **趋势预测**: 基于历史数据预测趋势

【分析方法】
1. **定义问题**: 明确分析目标和范围
2. **收集信息**: 获取相关数据和背景
3. **选择方法**: 选择合适的分析方法
4. **执行分析**: 使用工具进行分析
5. **解释结果**: 解释分析结果的含义
6. **提出建议**: 基于分析提出建议

【回答要求】
1. **逻辑性**: 分析过程逻辑清晰
2. **准确性**: 计算和推理准确无误
3. **全面性**: 从多个角度进行分析
4. **可读性**: 使用图表、列表等提高可读性
5. **中文回答**: 所有回答必须使用中文，不要使用英文
5. **实用性**: 提供可操作的建议

【注意事项】
1. 使用结构化的方式呈现分析结果
2. 对于复杂分析，分步骤说明
3. 使用数据和事实支持结论
4. 说明分析的局限性和假设
5. 提供清晰的总结和建议
"""

    async def execute(self, state: ChatState) -> Dict[str, Any]:
        """
        执行分析任务

        Args:
            state: 当前聊天状态

        Returns:
            更新后的状态字段
        """
        app_logger.info(f"[{self.name}] 开始执行分析任务...")

        # 获取任务指令
        task_instruction = state.get("task_instruction", "")
        if not task_instruction or task_instruction.strip() == "":
            app_logger.warning(f"[{self.name}] 未收到任务指令")
            return {
                "messages": [AIMessage(content="抱歉，我没有收到具体的分析任务指令。")]
            }

        app_logger.info(f"[{self.name}] 任务指令: {task_instruction[:100]}...")

        # 获取消息历史
        messages = state.get("messages", [])

        # 构建提示
        prompt_messages = [
            SystemMessage(content=self.system_prompt),
        ]

        # 添加对话历史（最近8条，分析任务可能需要较多上下文）
        # 过滤空消息
        if messages:
            recent_messages = messages[-8:] if len(messages) > 8 else messages
            for msg in recent_messages:
                if hasattr(msg, 'content') and msg.content and msg.content.strip():
                    prompt_messages.append(msg)
                else:
                    app_logger.warning(f"[{self.name}] 跳过空消息: {type(msg).__name__}")

        # 添加任务指令（确保不为空）
        task_content = f"【分析任务】\n{task_instruction}"
        if task_content.strip():
            prompt_messages.append(HumanMessage(content=task_content))
        else:
            app_logger.error(f"[{self.name}] 任务内容为空")
            return {
                "messages": [AIMessage(content="抱歉，任务内容为空，无法执行分析。")]
            }

        # 记录提示
        self._log_prompt(prompt_messages)

        # 调用 LLM（可能会调用工具）
        try:
            response = await self.llm_with_tools.ainvoke(prompt_messages)

            # 处理工具调用
            if hasattr(response, 'tool_calls') and response.tool_calls:
                app_logger.info(f"[{self.name}] 检测到工具调用: {len(response.tool_calls)} 个")

                # 执行工具调用
                tool_results = []
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]

                    app_logger.info(f"[{self.name}] 调用工具: {tool_name}")
                    app_logger.debug(f"[{self.name}] 工具参数: {tool_args}")

                    if tool_name in self.tool_map:
                        tool = self.tool_map[tool_name]
                        try:
                            result = await tool.ainvoke(tool_args)
                            tool_results.append({
                                "tool": tool_name,
                                "result": result
                            })
                            app_logger.info(f"[{self.name}] 工具 {tool_name} 执行成功")
                        except Exception as e:
                            app_logger.error(f"[{self.name}] 工具 {tool_name} 执行失败: {e}")
                            tool_results.append({
                                "tool": tool_name,
                                "error": str(e)
                            })
                    else:
                        app_logger.warning(f"[{self.name}] 未找到工具: {tool_name}")

                # 将工具结果添加到消息中，再次调用 LLM 生成最终响应
                prompt_messages.append(response)

                # 添加工具结果
                from langchain_core.messages import ToolMessage
                for i, tool_result in enumerate(tool_results):
                    # 确保 content 不为空
                    content = str(tool_result.get("result", tool_result.get("error", "")))
                    if not content or content.strip() == "":
                        content = "工具执行完成，但未返回结果"

                    tool_msg = ToolMessage(
                        content=content,
                        tool_call_id=response.tool_calls[i]["id"]
                    )
                    prompt_messages.append(tool_msg)

                # 再次调用 LLM 生成最终响应
                final_response = await self.llm.ainvoke(prompt_messages)
                response_text = final_response.content
            else:
                # 没有工具调用，直接使用响应
                response_text = response.content

            # 记录响应
            self._log_response(response_text)

            app_logger.info(f"[{self.name}] 分析任务完成")

            # 将响应添加到消息历史
            return {
                "messages": [AIMessage(content=response_text)]
            }

        except Exception as e:
            app_logger.error(f"[{self.name}] 执行失败: {e}")
            error_msg = f"抱歉，分析时遇到错误: {str(e)}"
            return {
                "messages": [AIMessage(content=error_msg)]
            }

    def _log_prompt(self, messages):
        """记录提示"""
        app_logger.info(f"[{self.name}] 📤 发送提示 (消息数: {len(messages)})")
        for i, msg in enumerate(messages):
            msg_type = msg.__class__.__name__
            content_preview = msg.content[:100] if len(msg.content) > 100 else msg.content
            app_logger.debug(f"  [{i+1}] {msg_type}: {content_preview}...")

    def _log_response(self, response: str):
        """记录响应"""
        preview = response[:200] if len(response) > 200 else response
        app_logger.info(f"[{self.name}] 📥 收到响应: {preview}...")

