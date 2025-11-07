"""
WriteAgent - 写入智能体

专门负责知识库写入、更新、删除等操作
"""
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain.tools import BaseTool
from src.config import settings
from src.utils import app_logger
from src.agent.multi_agent.chat_state import ChatState


class WriteAgent:
    """
    写入智能体 - Worker Agent
    
    职责：
    1. 接收 Supervisor 的写入任务指令
    2. 调用写入相关工具（添加、更新、删除知识）
    3. 确认操作结果并反馈
    
    专长：
    - 知识库写入
    - 内容更新
    - 数据删除
    - 批量操作
    """
    
    def __init__(self, llm: ChatOpenAI = None, tools: List[BaseTool] = None):
        """初始化写入智能体"""
        self.name = "WriteAgent"
        self.llm = llm or ChatOpenAI(
            model=settings.model_name,
            temperature=0.1,  # 极低温度，保持写入操作的准确性
            max_tokens=settings.max_tokens,
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_api_base,
        )
        
        # 过滤出写入相关的工具
        self.tools = self._filter_write_tools(tools or [])
        self.tool_map = {tool.name: tool for tool in self.tools}
        
        # 如果有工具，绑定到 LLM
        if self.tools:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
        else:
            self.llm_with_tools = self.llm
        
        self.system_prompt = self._get_system_prompt()
        
        app_logger.info(f"[{self.name}] 初始化完成，可用工具: {list(self.tool_map.keys())}")
    
    def _filter_write_tools(self, tools: List[BaseTool]) -> List[BaseTool]:
        """过滤出写入相关的工具"""
        write_keywords = ["add", "write", "update", "delete", "remove", "insert", "upload", "create"]
        filtered_tools = []
        
        for tool in tools:
            tool_name_lower = tool.name.lower()
            if any(keyword in tool_name_lower for keyword in write_keywords):
                filtered_tools.append(tool)
        
        # 如果没有找到写入工具，返回所有工具（向后兼容）
        if not filtered_tools:
            app_logger.warning(f"[{self.name}] 未找到写入相关工具，使用所有工具")
            return tools
        
        return filtered_tools
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        tool_descriptions = ""
        if self.tools:
            tool_descriptions = "\n【可用工具】\n"
            for tool in self.tools:
                tool_descriptions += f"- {tool.name}: {tool.description}\n"
        
        return f"""你是一个专业的写入智能体（WriteAgent），专门负责知识库的写入、更新和删除操作。

【核心职责】
1. 理解 Supervisor 给出的写入任务
2. 调用写入工具操作知识库
3. 验证操作结果
4. 向用户确认操作完成

{tool_descriptions}

【工作流程】
1. 仔细阅读写入任务指令
2. 提取要写入/更新/删除的内容
3. 调用合适的写入工具
4. 验证操作是否成功
5. 向用户确认操作结果

【操作类型】
1. **添加知识**: 将新内容添加到知识库
2. **更新知识**: 修改已有的知识内容
3. **删除知识**: 从知识库中删除内容
4. **批量操作**: 处理多条知识的添加/更新

【安全要求】
1. **确认操作**: 对于删除操作，确保理解用户意图
2. **数据验证**: 验证要写入的数据格式正确
3. **错误处理**: 操作失败时提供清晰的错误信息
4. **操作日志**: 记录所有写入操作
5. **回滚支持**: 如果可能，支持操作回滚

【回答要求】
1. **明确性**: 清楚说明执行了什么操作
2. **结果确认**: 告知用户操作是否成功
3. **详细信息**: 提供操作的详细信息（如添加了几条知识）
4. **错误说明**: 如果失败，说明失败原因
5. **后续建议**: 提供后续操作建议

【注意事项】
1. 写入前验证数据格式和内容
2. 操作完成后确认结果
3. 对于删除操作要特别谨慎
4. 提供清晰的操作反馈
5. 记录所有操作日志
"""
    
    async def execute(self, state: ChatState) -> Dict[str, Any]:
        """
        执行写入任务
        
        Args:
            state: 当前聊天状态
        
        Returns:
            更新后的状态字段
        """
        app_logger.info(f"[{self.name}] 开始执行写入任务...")
        
        # 获取任务指令
        task_instruction = state.get("task_instruction", "")
        if not task_instruction:
            app_logger.warning(f"[{self.name}] 未收到任务指令")
            return {}
        
        app_logger.info(f"[{self.name}] 任务指令: {task_instruction[:100]}...")
        
        # 获取消息历史
        messages = state["messages"]
        
        # 构建提示
        prompt_messages = [
            SystemMessage(content=self.system_prompt),
        ]
        
        # 添加对话历史（最近3条，写入任务通常只需要最近的上下文）
        recent_messages = messages[-3:] if len(messages) > 3 else messages
        prompt_messages.extend(recent_messages)
        
        # 添加任务指令
        prompt_messages.append(
            HumanMessage(content=f"【写入任务】\n{task_instruction}")
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
            
            app_logger.info(f"[{self.name}] 写入任务完成")
            
            # 将响应添加到消息历史
            return {
                "messages": [AIMessage(content=response_text)]
            }
            
        except Exception as e:
            app_logger.error(f"[{self.name}] 执行失败: {e}")
            error_msg = f"抱歉，写入操作时遇到错误: {str(e)}"
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

