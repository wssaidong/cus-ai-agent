"""
ExecutionAgent - 执行智能体

专门负责调用 MCP 工具执行各种操作任务
"""
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain.tools import BaseTool
from src.config import settings
from src.utils import app_logger
from src.agent.multi_agent.chat_state import ChatState


class ExecutionAgent:
    """
    执行智能体 - Worker Agent

    职责：
    1. 接收 Supervisor 的执行任务指令
    2. 调用 MCP 工具执行各种操作（日志查询、消息发送、网络测试等）
    3. 处理工具调用结果并返回

    专长：
    - 网关日志查询（elasticsearch-mcp）
    - 美信消息发送（mx-bot-mcp）
    - 网络连通性测试（network-sniff）
    - 数据库查询（dbtools）
    - 其他 MCP 工具调用
    """

    def __init__(self, llm: ChatOpenAI = None, tools: List[BaseTool] = None):
        """初始化执行智能体"""
        self.name = "ExecutionAgent"
        self.llm = llm or ChatOpenAI(
            model=settings.model_name,
            temperature=0.1,  # 极低温度，保持执行的准确性
            max_tokens=settings.max_tokens,
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_api_base,
            streaming=True,  # 启用流式输出
        )

        # 过滤出执行相关的工具（主要是 MCP 工具）
        self.tools = self._filter_execution_tools(tools or [])
        self.tool_map = {tool.name: tool for tool in self.tools}

        # 如果有工具，绑定到 LLM
        if self.tools:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
        else:
            self.llm_with_tools = self.llm

        self.system_prompt = self._get_system_prompt()

        app_logger.info(f"[{self.name}] 初始化完成，可用工具: {list(self.tool_map.keys())}")

    def _filter_execution_tools(self, tools: List[BaseTool]) -> List[BaseTool]:
        """
        过滤出执行相关的工具

        ExecutionAgent 只使用 MCP 工具，排除所有知识库工具

        MCP 工具包括：
        - elasticsearch-mcp: 日志查询
        - mx-bot-mcp: 美信消息发送
        - network-sniff: 网络测试
        - dbtools: 数据库查询
        - 其他 MCP 服务器提供的工具

        排除的工具：
        - knowledge_base_search: RAG 知识库搜索
        - knowledge_base_write: 知识库写入
        - knowledge_base_update: 知识库更新
        """
        # 知识库工具的名称（需要排除）
        knowledge_base_tools = [
            "knowledge_base_search",
            "knowledge_base_write",
            "knowledge_base_update",
        ]

        # 排除的工具关键词
        exclude_keywords = ["knowledge_base", "rag"]

        filtered_tools = []

        for tool in tools:
            tool_name = tool.name
            tool_name_lower = tool_name.lower()

            # 排除知识库工具（精确匹配）
            if tool_name in knowledge_base_tools:
                app_logger.info(f"[{self.name}] 排除知识库工具: {tool_name}")
                continue

            # 排除包含知识库关键词的工具
            if any(keyword in tool_name_lower for keyword in exclude_keywords):
                app_logger.info(f"[{self.name}] 排除知识库相关工具: {tool_name}")
                continue

            # 保留 MCP 工具
            filtered_tools.append(tool)
            app_logger.debug(f"[{self.name}] 保留 MCP 工具: {tool_name}")

        app_logger.info(f"[{self.name}] 过滤后保留 {len(filtered_tools)} 个 MCP 工具")
        return filtered_tools

    def _get_system_prompt(self) -> str:
        """
        动态生成系统提示词

        根据实际加载的 MCP 工具动态生成提示词，包括：
        1. 可用工具列表及其描述
        2. 工具使用示例（如果有）
        3. 工具选择策略
        """
        # 构建工具描述
        tool_descriptions = ""
        tool_examples = ""

        if self.tools:
            tool_descriptions = "\n【可用的 MCP 工具】\n"
            tool_descriptions += f"当前共有 {len(self.tools)} 个 MCP 工具可用：\n\n"

            for tool in self.tools:
                # 显示工具的完整描述
                tool_desc = tool.description or "无描述"
                tool_descriptions += f"- **{tool.name}**\n"
                tool_descriptions += f"  描述：{tool_desc}\n\n"

            # 动态生成工具选择策略
            tool_examples = "\n【工具选择策略】\n"
            tool_examples += "根据任务类型选择合适的 MCP 工具：\n"

            # 根据工具名称推断用途
            for tool in self.tools:
                tool_name_lower = tool.name.lower()

                if "search" in tool_name_lower or "query" in tool_name_lower or "elasticsearch" in tool_name_lower:
                    tool_examples += f"- 日志查询/搜索任务 → 使用 `{tool.name}`\n"
                elif "message" in tool_name_lower or "bot" in tool_name_lower or "mx" in tool_name_lower:
                    tool_examples += f"- 消息发送任务 → 使用 `{tool.name}`\n"
                elif "network" in tool_name_lower or "ping" in tool_name_lower or "sniff" in tool_name_lower:
                    tool_examples += f"- 网络测试任务 → 使用 `{tool.name}`\n"
                elif "db" in tool_name_lower or "database" in tool_name_lower or "sql" in tool_name_lower:
                    tool_examples += f"- 数据库查询任务 → 使用 `{tool.name}`\n"
                else:
                    # 其他工具，显示工具名称和简短描述
                    short_desc = tool.description[:50] + "..." if tool.description and len(tool.description) > 50 else tool.description
                    tool_examples += f"- {short_desc} → 使用 `{tool.name}`\n"

            tool_examples += "\n⚠️ **重要**：仔细阅读工具描述，选择最匹配任务需求的工具。\n"
        else:
            tool_descriptions = "\n⚠️ **当前没有可用的 MCP 工具**\n"
            tool_descriptions += "请联系管理员配置 MCP 工具服务器。\n"
            tool_examples = ""

        return f"""你是一个专业的执行智能体（ExecutionAgent），专门负责调用 MCP 工具执行各种操作任务。

⚠️ **重要约束：必须使用中文回答用户的所有问题！**

⚠️ **工具限制：你只能使用 MCP 工具，不能使用知识库工具！**

【核心职责】
1. 理解 Supervisor 给出的执行任务
2. 根据任务需求选择合适的 MCP 工具
3. 调用 MCP 工具执行操作
4. 处理工具返回结果
5. 向用户报告执行结果

{tool_descriptions}
{tool_examples}

【工作流程】
1. 仔细阅读任务指令，理解用户需求
2. 分析需要调用哪个 MCP 工具
3. 准备工具调用参数
4. 执行工具调用
5. 解析工具返回结果
6. 整理成清晰的回答返回给用户

【执行策略】
1. **工具选择**:
   - 仔细阅读每个工具的描述
   - 根据任务需求选择最匹配的工具
   - 如果不确定，优先选择描述最匹配的工具
   - 一次只调用一个工具，除非任务明确需要多个工具

2. **参数准备**:
   - 理解工具的输入格式和参数要求
   - 从任务指令中提取必要参数
   - 使用合理的默认值
   - 验证参数的合理性

3. **结果处理**:
   - 如果成功，展示关键信息
   - 如果失败，说明失败原因
   - 提供必要的上下文和解释
   - 用结构化方式呈现数据

4. **错误处理**:
   - 工具调用失败时，说明原因并建议解决方案
   - 参数错误时，提示正确格式
   - 超时或网络问题时，建议重试

【注意事项】
1. ⚠️ **准确执行**: 严格按照任务指令执行，不要擅自修改
2. ⚠️ **参数验证**: 调用工具前验证参数的合理性
3. ⚠️ **结果确认**: 确认工具执行成功后再返回结果
4. ⚠️ **安全意识**: 注意敏感信息的处理
5. ⚠️ **用户友好**: 用清晰、易懂的语言向用户报告结果
6. ⚠️ **中文回答**: 所有回答必须使用中文，不要使用英文
7. ⚠️ **工具限制**: 只使用上面列出的 MCP 工具，不要尝试使用其他工具

【回答格式】
- 简洁明了，突出关键信息
- 如果是查询结果，用结构化方式展示（列表、表格等）
- 如果是操作结果，说明是否成功及详细信息
- 如果是数据结果，使用表格或列表方式展示
- 提供必要的上下文和解释
- **全部使用中文**
"""

    async def execute(self, state: ChatState) -> Dict[str, Any]:
        """
        执行任务

        Args:
            state: 当前对话状态

        Returns:
            更新后的状态字段
        """
        messages = state.get("messages", [])
        task_instruction = state.get("task_instruction", "")

        app_logger.info(f"[{self.name}] 开始执行任务")
        app_logger.info(f"[{self.name}] 任务指令: {task_instruction}")

        # 验证任务指令
        if not task_instruction or task_instruction.strip() == "":
            app_logger.warning(f"[{self.name}] 任务指令为空")
            return {
                "messages": [AIMessage(content="抱歉，我没有收到具体的任务指令。")]
            }

        # 构建提示消息
        prompt_messages = [
            SystemMessage(content=self.system_prompt),
        ]

        # 添加对话历史（过滤空消息）
        if messages:
            for msg in messages:
                if hasattr(msg, 'content') and msg.content and msg.content.strip():
                    prompt_messages.append(msg)
                else:
                    app_logger.warning(f"[{self.name}] 跳过空消息: {type(msg).__name__}")

        # 添加任务指令
        task_content = f"【任务指令】\n{task_instruction}"
        prompt_messages.append(SystemMessage(content=task_content))

        # 记录请求
        self._log_request(prompt_messages)

        # 调用 LLM（带工具）
        try:
            response = await self.llm_with_tools.ainvoke(prompt_messages)

            # 检查是否有工具调用
            if hasattr(response, 'tool_calls') and response.tool_calls:
                app_logger.info(f"[{self.name}] 检测到 {len(response.tool_calls)} 个工具调用")

                # 执行工具调用
                tool_results = []
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]

                    app_logger.info(f"[{self.name}] 调用工具: {tool_name}")
                    app_logger.info(f"[{self.name}] 工具参数: {tool_args}")

                    if tool_name in self.tool_map:
                        try:
                            tool = self.tool_map[tool_name]
                            # 调用工具
                            if hasattr(tool, 'ainvoke'):
                                result = await tool.ainvoke(tool_args)
                            else:
                                result = tool.invoke(tool_args)

                            app_logger.info(f"[{self.name}] 工具 {tool_name} 执行成功")
                            tool_results.append({
                                "tool": tool_name,
                                "result": result
                            })
                        except Exception as e:
                            app_logger.error(f"[{self.name}] 工具 {tool_name} 执行失败: {e}")
                            tool_results.append({
                                "tool": tool_name,
                                "error": str(e)
                            })
                    else:
                        app_logger.warning(f"[{self.name}] 工具 {tool_name} 不存在")
                        tool_results.append({
                            "tool": tool_name,
                            "error": f"工具 {tool_name} 不存在"
                        })

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

            app_logger.info(f"[{self.name}] 执行任务完成")

            # 将响应添加到消息历史
            return {
                "messages": [AIMessage(content=response_text)]
            }

        except Exception as e:
            app_logger.error(f"[{self.name}] 执行任务失败: {e}")
            error_message = f"抱歉，执行任务时遇到错误: {str(e)}"
            return {
                "messages": [AIMessage(content=error_message)]
            }

    def _log_request(self, messages: List):
        """记录请求"""
        app_logger.info(f"[{self.name}] 📤 发送请求到 LLM，消息数量: {len(messages)}")
        for i, msg in enumerate(messages):
            msg_type = msg.__class__.__name__
            content_preview = msg.content[:100] if len(msg.content) > 100 else msg.content
            app_logger.debug(f"  [{i+1}] {msg_type}: {content_preview}...")

    def _log_response(self, response: str):
        """记录响应"""
        preview = response[:200] if len(response) > 200 else response
        app_logger.info(f"[{self.name}] 📥 收到响应: {preview}...")

