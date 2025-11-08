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
        
        主要包括：
        - MCP 工具（日志查询、消息发送、网络测试、数据库查询等）
        - 排除知识库相关工具（search、write、update）
        """
        # 排除的工具关键词（知识库相关）
        exclude_keywords = ["knowledge_base", "rag"]
        
        filtered_tools = []
        
        for tool in tools:
            tool_name_lower = tool.name.lower()
            # 排除知识库工具
            if any(keyword in tool_name_lower for keyword in exclude_keywords):
                continue
            
            # 包含其他所有工具（主要是 MCP 工具）
            filtered_tools.append(tool)
        
        return filtered_tools
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        tool_descriptions = ""
        if self.tools:
            tool_descriptions = "\n【可用工具】\n"
            for tool in self.tools:
                # 显示工具的完整描述（包含服务器描述）
                tool_desc = tool.description or "无描述"
                tool_descriptions += f"- **{tool.name}**: {tool_desc}\n"
        else:
            tool_descriptions = "\n⚠️ 当前没有可用工具\n"
        
        return f"""你是一个专业的执行智能体（ExecutionAgent），专门负责调用 MCP 工具执行各种操作任务。

【核心职责】
1. 理解 Supervisor 给出的执行任务
2. 选择合适的 MCP 工具
3. 调用工具执行操作
4. 处理工具返回结果
5. 向用户报告执行结果

{tool_descriptions}

【工作流程】
1. 仔细阅读任务指令，理解用户需求
2. 分析需要调用哪个工具
3. 准备工具调用参数
4. 执行工具调用
5. 解析工具返回结果
6. 整理成清晰的回答返回给用户

【执行策略】
1. **工具选择**: 根据任务描述和工具能力，选择最合适的工具
   - 日志查询 → elasticsearch-mcp 的 search 工具
   - 消息发送 → mx-bot-mcp 工具
   - 网络测试 → network-sniff 工具
   - 数据库查询 → dbtools 工具

2. **参数准备**: 仔细准备工具调用参数
   - 理解工具的输入格式
   - 从任务指令中提取必要参数
   - 使用合理的默认值

3. **结果处理**: 清晰呈现执行结果
   - 如果成功，展示关键信息
   - 如果失败，说明失败原因
   - 提供必要的上下文和解释

4. **错误处理**: 优雅处理错误
   - 工具调用失败时，说明原因
   - 参数错误时，提示正确格式
   - 超时或网络问题时，建议重试

【注意事项】
1. ⚠️ **准确执行**: 严格按照任务指令执行，不要擅自修改
2. ⚠️ **参数验证**: 调用工具前验证参数的合理性
3. ⚠️ **结果确认**: 确认工具执行成功后再返回结果
4. ⚠️ **安全意识**: 注意敏感信息的处理
5. ⚠️ **用户友好**: 用清晰、易懂的语言向用户报告结果

【回答格式】
- 简洁明了，突出关键信息
- 如果是查询结果，用结构化方式展示
- 如果是操作结果，说明是否成功
- 提供必要的上下文和解释
"""
    
    async def execute(self, state: ChatState) -> Dict[str, Any]:
        """
        执行任务
        
        Args:
            state: 当前对话状态
            
        Returns:
            更新后的状态字段
        """
        messages = state["messages"]
        task_instruction = state.get("task_instruction", "")
        
        app_logger.info(f"[{self.name}] 开始执行任务")
        app_logger.info(f"[{self.name}] 任务指令: {task_instruction}")
        
        # 构建提示消息
        prompt_messages = [
            SystemMessage(content=self.system_prompt),
        ]
        
        # 添加对话历史
        prompt_messages.extend(messages)
        
        # 如果有任务指令，添加为系统消息
        if task_instruction:
            prompt_messages.append(
                SystemMessage(content=f"【任务指令】\n{task_instruction}")
            )
        
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

