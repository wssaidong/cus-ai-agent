"""
智能体节点定义
"""
from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from src.config import settings
from src.utils import app_logger
from src.tools import get_available_tools
from .state import AgentState


# 初始化默认LLM
llm = ChatOpenAI(
    model=settings.model_name,
    temperature=settings.temperature,
    max_tokens=settings.max_tokens,
    openai_api_key=settings.openai_api_key,
    openai_api_base=settings.openai_api_base,
)

# 获取工具
tools = get_available_tools()

# 创建提示模板
prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content="""你是一个智能助手，可以使用各种工具来帮助用户解决问题。

你可以使用以下工具：
- calculator: 执行数学计算
- text_process: 处理文本（大小写转换、反转、长度等）
- api_call: 调用外部HTTP API
- database_query: 查询数据库（如果启用）
- knowledge_base_search: 从知识库中搜索相关信息（RAG工具）
- api-info-by-code: 根据API编码查询API详细信息（MCP工具）

请根据用户的问题，选择合适的工具来完成任务。
当用户询问文档、资料、知识点等信息时，优先使用 knowledge_base_search 工具。
如果不需要使用工具，直接回答即可。
"""),
    MessagesPlaceholder(variable_name="chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# 创建默认智能体
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=settings.max_iterations,
    handle_parsing_errors=True,
)


def create_dynamic_agent_executor(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> AgentExecutor:
    """
    创建动态智能体执行器

    Args:
        model: 模型名称，如果为None则使用配置文件中的模型
        temperature: 温度参数
        max_tokens: 最大token数

    Returns:
        AgentExecutor: 智能体执行器
    """
    # 创建动态LLM
    dynamic_llm = ChatOpenAI(
        model=model or settings.model_name,
        temperature=temperature or settings.temperature,
        max_tokens=max_tokens or settings.max_tokens,
        openai_api_key=settings.openai_api_key,
        openai_api_base=settings.openai_api_base,
    )

    # 创建动态智能体
    dynamic_agent = create_openai_tools_agent(dynamic_llm, tools, prompt)
    dynamic_executor = AgentExecutor(
        agent=dynamic_agent,
        tools=tools,
        verbose=True,
        max_iterations=settings.max_iterations,
        handle_parsing_errors=True,
    )

    return dynamic_executor


def entry_node(state: AgentState) -> AgentState:
    """入口节点：初始化状态"""
    app_logger.info("进入入口节点")
    
    if not state.get("metadata"):
        state["metadata"] = {}
    
    if not state.get("tool_results"):
        state["tool_results"] = []
    
    if not state.get("intermediate_steps"):
        state["intermediate_steps"] = []
    
    state["iteration"] = state.get("iteration", 0)
    state["is_finished"] = False
    
    return state


def llm_node(state: AgentState) -> AgentState:
    """LLM节点：调用大模型进行推理"""
    app_logger.info("进入LLM节点")
    
    try:
        # 获取最后一条消息
        messages = state.get("messages", [])
        if not messages:
            state["final_response"] = "错误：没有输入消息"
            state["is_finished"] = True
            return state
        
        last_message = messages[-1]
        user_input = last_message.content if hasattr(last_message, 'content') else str(last_message)
        
        # 执行智能体
        result = agent_executor.invoke({
            "input": user_input,
            "chat_history": messages[:-1] if len(messages) > 1 else [],
        })
        
        # 更新状态
        state["final_response"] = result.get("output", "")
        state["intermediate_steps"] = result.get("intermediate_steps", [])
        state["is_finished"] = True
        
        # 更新元数据
        state["metadata"]["llm_calls"] = state["metadata"].get("llm_calls", 0) + 1
        
        app_logger.info(f"LLM响应: {state['final_response'][:100]}...")
        
    except Exception as e:
        app_logger.error(f"LLM节点执行失败: {str(e)}")
        state["final_response"] = f"处理失败: {str(e)}"
        state["is_finished"] = True
    
    return state


def output_node(state: AgentState) -> AgentState:
    """输出节点：格式化输出"""
    app_logger.info("进入输出节点")
    
    # 确保有最终响应
    if not state.get("final_response"):
        state["final_response"] = "抱歉，我无法生成响应。"
    
    # 添加响应消息到历史
    if state.get("final_response"):
        messages = state.get("messages", [])
        messages.append(AIMessage(content=state["final_response"]))
        state["messages"] = messages
    
    state["is_finished"] = True
    
    return state


def should_continue(state: AgentState) -> str:
    """决策函数：判断是否继续"""
    if state.get("is_finished"):
        return "end"
    
    iteration = state.get("iteration", 0)
    if iteration >= settings.max_iterations:
        app_logger.warning(f"达到最大迭代次数: {settings.max_iterations}")
        return "end"
    
    return "continue"

