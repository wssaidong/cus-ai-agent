"""
SearchAgent - 搜索智能体

专门负责知识库搜索和信息检索任务
"""
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain.tools import BaseTool
from src.config import settings
from src.utils import app_logger
from src.agent.multi_agent.chat_state import ChatState


class SearchAgent:
    """
    搜索智能体 - Worker Agent

    职责：
    1. 接收 Supervisor 的搜索任务指令
    2. 调用搜索相关工具（RAG、知识库查询等）
    3. 整理和呈现搜索结果

    专长：
    - 知识库搜索
    - 信息检索
    - 相关性排序
    - 结果摘要
    """

    def __init__(self, llm: ChatOpenAI = None, tools: List[BaseTool] = None):
        """初始化搜索智能体"""
        self.name = "SearchAgent"
        self.llm = llm or ChatOpenAI(
            model=settings.model_name,
            temperature=0.3,  # 较低温度，保持搜索结果的准确性
            max_tokens=settings.max_tokens,
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_api_base,
            streaming=True,  # 启用流式输出
        )

        # 过滤出搜索相关的工具
        self.tools = self._filter_search_tools(tools or [])
        self.tool_map = {tool.name: tool for tool in self.tools}

        # 如果有工具，绑定到 LLM
        if self.tools:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
        else:
            self.llm_with_tools = self.llm

        self.system_prompt = self._get_system_prompt()

        app_logger.info(f"[{self.name}] 初始化完成，可用工具: {list(self.tool_map.keys())}")

    def _filter_search_tools(self, tools: List[BaseTool]) -> List[BaseTool]:
        """过滤出搜索相关的工具"""
        search_keywords = ["search", "query", "retrieve", "find", "lookup", "rag"]
        filtered_tools = []

        for tool in tools:
            tool_name_lower = tool.name.lower()
            if any(keyword in tool_name_lower for keyword in search_keywords):
                filtered_tools.append(tool)

        # 如果没有找到搜索工具，返回所有工具（向后兼容）
        if not filtered_tools:
            app_logger.warning(f"[{self.name}] 未找到搜索相关工具，使用所有工具")
            return tools

        return filtered_tools

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        tool_descriptions = ""
        if self.tools:
            tool_descriptions = "\n【可用工具】\n"
            for tool in self.tools:
                tool_descriptions += f"- {tool.name}: {tool.description}\n"

        return f"""你是一个专业的搜索智能体（SearchAgent），专门负责知识库搜索和信息检索。

⚠️ **重要约束：必须使用中文回答用户的所有问题！**

【核心职责】
1. 理解 Supervisor 给出的搜索任务
2. 调用搜索工具查询知识库
3. 整理和呈现搜索结果
4. 提供准确、相关的信息

{tool_descriptions}

【工作流程】
1. 仔细阅读搜索任务指令
2. 提取核心查询意图和关键词
3. 调用知识库搜索工具
4. 分析搜索结果的相关性和质量
5. 整理成清晰、易懂的回答

【搜索策略优化】
1. **精准查询**:
   - 提取问题的核心关键词
   - 去除无关的修饰词和停用词
   - 保持查询的简洁性和针对性

2. **相关性评估**:
   - 优先使用相似度高（≥80%）的结果
   - 相似度60-80%的结果需要仔细甄别
   - 相似度<60%的结果谨慎使用，需说明可能不够相关

3. **结果整合**:
   - 综合多个相关结果，提供完整答案
   - 如果结果之间有矛盾，说明差异并标注来源
   - 按相关性和重要性组织信息

4. **质量控制**:
   - 确保答案直接回应用户问题
   - 避免包含无关信息
   - 如果搜索结果不够准确，诚实说明

【回答要求】
1. **准确性**:
   - 确保信息来自知识库，不编造
   - 引用时保持原文准确性
   - 如有不确定，明确说明

2. **完整性**:
   - 提供全面的搜索结果
   - 涵盖问题的各个方面
   - 必要时综合多个来源

3. **清晰性**:
   - 使用清晰的结构组织信息
   - 采用列表、步骤、分点等格式
   - 突出重点信息

4. **相关性**:
   - 只返回与问题直接相关的信息
   - 过滤掉低相关度的内容
   - 说明信息与问题的关联

5. **来源性**:
   - 标注信息来源（文件名、文档名等）
   - 说明相似度分数
   - 便于用户追溯和验证

6. **中文回答**:
   - 所有回答必须使用中文
   - 保持语言流畅自然

【注意事项】
1. 如果搜索结果为空，诚实告知用户，并建议：
   - 尝试不同的关键词
   - 检查问题表述是否清晰
   - 确认知识库中是否有相关内容

2. 如果结果相关性不高（<60%），需要：
   - 明确说明结果可能不够准确
   - 建议用户调整问题或提供更多上下文
   - 可以尝试提供部分相关信息作为参考

3. 优先使用高质量结果：
   - 相似度≥80%的结果最可靠
   - 有完整元数据的结果更可信
   - 内容长度适中（200-2000字）的结果通常质量更好

4. 格式化输出：
   - 使用Markdown格式
   - 重要信息用**加粗**
   - 使用列表和分段提高可读性

5. **全部使用中文回答，不要使用英文**
"""

    async def execute(self, state: ChatState) -> Dict[str, Any]:
        """
        执行搜索任务

        Args:
            state: 当前聊天状态

        Returns:
            更新后的状态字段
        """
        app_logger.info(f"[{self.name}] 开始执行搜索任务...")

        # 获取任务指令
        task_instruction = state.get("task_instruction", "")
        if not task_instruction or task_instruction.strip() == "":
            app_logger.warning(f"[{self.name}] 未收到任务指令")
            return {
                "messages": [AIMessage(content="抱歉，我没有收到具体的搜索任务指令。")]
            }

        app_logger.info(f"[{self.name}] 任务指令: {task_instruction[:100]}...")

        # 获取消息历史
        messages = state.get("messages", [])

        # 构建提示
        prompt_messages = [
            SystemMessage(content=self.system_prompt),
        ]

        # 添加对话历史（最近5条，搜索任务通常不需要太多历史）
        # 过滤空消息
        if messages:
            recent_messages = messages[-5:] if len(messages) > 5 else messages
            for msg in recent_messages:
                if hasattr(msg, 'content') and msg.content and msg.content.strip():
                    prompt_messages.append(msg)
                else:
                    app_logger.warning(f"[{self.name}] 跳过空消息: {type(msg).__name__}")

        # 添加任务指令（确保不为空）
        task_content = f"【搜索任务】\n{task_instruction}"
        if task_content.strip():
            prompt_messages.append(HumanMessage(content=task_content))
        else:
            app_logger.error(f"[{self.name}] 任务内容为空")
            return {
                "messages": [AIMessage(content="抱歉，任务内容为空，无法执行搜索。")]
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

            app_logger.info(f"[{self.name}] 搜索任务完成")

            # 将响应添加到消息历史
            return {
                "messages": [AIMessage(content=response_text)]
            }

        except Exception as e:
            app_logger.error(f"[{self.name}] 执行失败: {e}")
            error_msg = f"抱歉，搜索时遇到错误: {str(e)}"
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

