"""
Executor 智能体 - 执行者

负责执行具体任务，如搜索信息、生成内容等
"""
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain.tools import BaseTool
from src.config import settings
from src.utils import app_logger
from src.agent.multi_agent.chat_state import ChatState


class ExecutorAgent:
    """
    执行者智能体

    职责：
    1. 接收 Planner 的执行指令
    2. 调用工具完成具体任务
    3. 生成结构化的响应
    """

    def __init__(self, llm: ChatOpenAI = None, tools: List[BaseTool] = None):
        """初始化执行者"""
        self.name = "Executor"
        self.llm = llm or ChatOpenAI(
            model=settings.model_name,
            temperature=0.7,  # 适中温度，保持创造性
            max_tokens=settings.max_tokens,
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_api_base,
        )

        self.tools = tools or []
        self.tool_map = {tool.name: tool for tool in self.tools}

        # 如果有工具，绑定到 LLM
        if self.tools:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
        else:
            self.llm_with_tools = self.llm

        self.system_prompt = self._get_system_prompt()

        app_logger.info(f"[{self.name}] 初始化完成，可用工具: {list(self.tool_map.keys())}")

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        tool_descriptions = ""
        if self.tools:
            tool_descriptions = "\n【可用工具】\n"
            for tool in self.tools:
                tool_descriptions += f"- {tool.name}: {tool.description}\n"

        return f"""你是一个智能执行者（Executor），负责执行具体任务。

【核心职责】
1. 理解规划者（Planner）给出的执行指令
2. 调用合适的工具完成任务
3. 生成清晰、准确的响应

{tool_descriptions}

【工作流程】
1. 仔细阅读执行指令
2. 查看对话历史，理解上下文
3. 如果需要，调用工具获取信息
4. 整理信息，生成专业的回答
5. 确保回答准确、完整、易懂

【回答要求】
1. 准确性：确保信息准确无误
2. 完整性：全面回答用户问题
3. 清晰性：使用清晰的语言和结构
4. 专业性：保持专业的态度
5. 友好性：语气友好、乐于助人

【注意事项】
1. 如果工具返回的信息不足，说明情况
2. 如果无法完成任务，诚实告知用户
3. 引用知识库信息时说明来源
4. 适当使用格式化（如列表、步骤等）提高可读性
5. 使用工具时说明选择理由
"""

    async def execute(self, state: ChatState) -> Dict[str, Any]:
        """
        执行任务

        Args:
            state: 当前聊天状态

        Returns:
            更新后的状态字段
        """
        app_logger.info(f"[{self.name}] 开始执行任务...")

        # 获取执行指令
        instruction = state.get("execution_instruction", "")
        if not instruction:
            app_logger.warning(f"[{self.name}] 未收到执行指令")
            return {}

        app_logger.info(f"[{self.name}] 执行指令: {instruction[:100]}...")

        # 获取消息历史
        messages = state["messages"]

        # 构建提示
        prompt_messages = [
            SystemMessage(content=self.system_prompt),
        ]

        # 添加对话历史（最近10条）
        recent_messages = messages[-10:] if len(messages) > 10 else messages
        prompt_messages.extend(recent_messages)

        # 添加执行指令
        prompt_messages.append(
            HumanMessage(content=f"【执行指令】\n{instruction}")
        )

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
                    tool_msg = ToolMessage(
                        content=str(tool_result.get("result", tool_result.get("error", ""))),
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

            app_logger.info(f"[{self.name}] 任务执行完成")

            # 将响应添加到消息历史
            return {
                "messages": [AIMessage(content=response_text)]
            }

        except Exception as e:
            app_logger.error(f"[{self.name}] 执行失败: {e}")
            error_msg = f"抱歉，执行任务时遇到错误: {str(e)}"
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

