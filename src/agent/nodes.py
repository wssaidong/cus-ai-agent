"""
智能体节点定义
"""
from typing import Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from src.config import settings
from src.utils import app_logger
from src.tools import get_available_tools
from .state import AgentState
from .decision_engine import get_decision_engine, DecisionType


# 初始化默认LLM
llm = ChatOpenAI(
    model=settings.model_name,
    temperature=settings.temperature,
    max_tokens=settings.max_tokens,
    openai_api_key=settings.openai_api_key,
    openai_api_base=settings.openai_api_base,
)

# 获取工具（包含 MCP 工具）
tools = get_available_tools(include_mcp=True)

# 创建提示模板
prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content="""你是一个智能助手，可以使用各种工具来帮助用户解决问题。

【智能决策系统】
系统已为您分析了用户的问题类型，并提供了推荐的工具和决策建议。
请根据以下信息进行智能决策：

【决策信息】（在输入中会包含）：
- 问题类型：系统识别的问题类型
- 推荐工具：最适合的工具列表
- 置信度：系统对决策的置信度
- 推理说明：为什么选择这些工具

【重要原则】知识库优先策略：
在回答任何问题之前，首先判断是否可以从知识库中获取信息。知识库包含了经过验证的准确信息，应该作为首选信息来源。

【必须使用知识库的场景】：
1. 用户询问任何文档、资料、规范、标准相关的问题
2. 用户询问API、接口、功能、配置等技术细节
3. 用户询问产品功能、使用方法、操作步骤
4. 用户询问概念、定义、术语解释
5. 用户询问历史记录、已有信息、存档内容
6. 任何可能在知识库中存在的信息查询

【工具使用决策流程】：
第一步：查看系统提供的决策信息
  - 如果推荐使用 knowledge_base_search → 立即使用该工具

第二步：根据工具返回结果判断
  - 如果知识库有相关信息 → 基于知识库内容回答
  - 如果知识库无相关信息 → 基于通用知识回答

【可用工具列表】：
- knowledge_base_search: 从知识库中搜索相关信息（RAG工具）

【回答要求】：
1. 优先基于知识库内容回答，确保信息准确性
2. 如果知识库中有相关信息，必须引用并说明来源
3. 如果知识库中没有找到信息，明确告知用户
4. 避免在有知识库信息的情况下使用通用知识回答
5. 回答要完整、准确、有条理
6. 在使用工具时，说明为什么选择该工具
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

    # 获取最新的工具列表（包含 MCP 工具）
    current_tools = get_available_tools(include_mcp=True)

    # 创建动态智能体
    dynamic_agent = create_openai_tools_agent(dynamic_llm, current_tools, prompt)
    dynamic_executor = AgentExecutor(
        agent=dynamic_agent,
        tools=current_tools,
        verbose=True,
        max_iterations=settings.max_iterations,
        handle_parsing_errors=True,
    )

    return dynamic_executor


def _build_decision_hint(decision_result) -> str:
    """
    构建决策提示信息

    Args:
        decision_result: 决策结果对象

    Returns:
        格式化的决策提示字符串
    """
    hint = f"""【智能决策信息】
问题类型: {decision_result.decision_type.value}
置信度: {decision_result.confidence:.2%}
推理: {decision_result.reasoning}
推荐工具: {', '.join(decision_result.recommended_tools) if decision_result.recommended_tools else '无特定工具推荐'}
是否搜索知识库: {'是' if decision_result.should_search_kb else '否'}

请根据上述决策信息选择合适的工具来回答问题。"""
    return hint


def _check_knowledge_base_relevance(query: str) -> Optional[str]:
    """
    预检查知识库相关性

    Args:
        query: 用户查询

    Returns:
        如果查询与知识库高度相关，返回知识库搜索结果；否则返回None
    """
    # 定义知识库相关的关键词
    knowledge_keywords = [
        "文档", "资料", "手册", "规范", "标准", "说明",
        "API", "接口", "功能", "配置", "参数",
        "如何", "怎么", "什么是", "怎样", "方法",
        "教程", "指南", "步骤", "流程",
        "定义", "概念", "术语", "解释",
        "知识库", "查询", "搜索"
    ]

    # 检查查询是否包含知识库相关关键词
    query_lower = query.lower()
    is_relevant = any(keyword in query_lower for keyword in knowledge_keywords)

    if is_relevant:
        try:
            # 如果相关，预先搜索知识库
            if settings.enable_rag_tool:
                from src.tools.rag_tool import get_knowledge_base
                kb = get_knowledge_base()
                results = kb.search_with_score(query, top_k=3)  # 预检查只取前3个结果

                if results and len(results) > 0:
                    # 检查最高相似度
                    top_similarity = 1 - results[0][1]
                    if top_similarity >= 0.6:  # 相似度阈值
                        app_logger.info(f"知识库预检查命中，最高相似度: {top_similarity:.2%}")
                        return f"【知识库预检查】发现高度相关内容（相似度: {top_similarity:.2%}），使用 knowledge_base_search 工具获取详细信息。"
        except Exception as e:
            app_logger.warning(f"知识库预检查失败: {str(e)}")

    return None


def entry_node(state: AgentState) -> AgentState:
    """入口节点：初始化状态"""
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
    try:
        # 获取最后一条消息
        messages = state.get("messages", [])
        if not messages:
            state["final_response"] = "错误：没有输入消息"
            state["is_finished"] = True
            return state

        last_message = messages[-1]
        user_input = last_message.content if hasattr(last_message, 'content') else str(last_message)

        # 使用决策引擎进行智能决策
        decision_engine = get_decision_engine()
        decision_result = decision_engine.decide(user_input)

        app_logger.info(
            f"智能决策结果 - 类型: {decision_result.decision_type.value}, "
            f"置信度: {decision_result.confidence:.2%}, "
            f"推荐工具: {decision_result.recommended_tools}"
        )

        # 构建决策提示
        decision_hint = _build_decision_hint(decision_result)

        # 增强输入：添加决策信息
        enhanced_input = f"{user_input}\n\n{decision_hint}"

        # 执行智能体
        result = agent_executor.invoke({
            "input": enhanced_input,
            "chat_history": messages[:-1] if len(messages) > 1 else [],
        })

        # 更新状态
        state["final_response"] = result.get("output", "")
        state["intermediate_steps"] = result.get("intermediate_steps", [])
        state["is_finished"] = True

        # 更新元数据
        state["metadata"]["llm_calls"] = state["metadata"].get("llm_calls", 0) + 1
        state["metadata"]["decision_type"] = decision_result.decision_type.value
        state["metadata"]["decision_confidence"] = decision_result.confidence
        state["metadata"]["recommended_tools"] = decision_result.recommended_tools
        state["metadata"]["should_search_kb"] = decision_result.should_search_kb

    except Exception as e:
        app_logger.error(f"LLM节点执行失败: {str(e)}")
        state["final_response"] = f"处理失败: {str(e)}"
        state["is_finished"] = True

    return state


def output_node(state: AgentState) -> AgentState:
    """输出节点：格式化输出"""
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

