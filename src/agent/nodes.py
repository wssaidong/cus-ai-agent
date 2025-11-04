"""
智能体节点定义
"""
from typing import Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
try:
    from langchain.agents import AgentExecutor, create_openai_tools_agent
except ImportError:
    from langgraph.prebuilt import create_react_agent
    AgentExecutor = None
    create_openai_tools_agent = None
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
    SystemMessage(content="""你是一个智能助手，能够使用多种工具帮助用户解决问题。

## 核心原则：知识库优先策略

在回答问题前，优先从知识库获取信息。知识库包含经过验证的准确信息，是首选信息来源。

### 必须使用知识库的场景
- 文档、资料、规范、标准相关问题
- API、接口、功能、配置等技术细节
- 产品功能、使用方法、操作步骤
- 概念、定义、术语解释
- 历史记录、已有信息、存档内容
- 任何可能存在于知识库的信息查询

## 智能决策系统

系统已分析用户问题并提供决策建议（包含在输入中）：
- **问题类型**：系统识别的问题分类
- **推荐工具**：最适合的工具列表
- **置信度**：决策可信程度
- **推理说明**：工具选择理由

## 决策流程

1. **检查决策信息**
   - 若推荐 `knowledge_base_search` → 立即使用该工具
   - 若推荐其他工具 → 根据推荐使用相应工具

2. **处理工具结果**
   - 知识库有相关信息 → 基于知识库内容回答，并引用来源
   - 知识库无相关信息 → 明确告知用户，再基于通用知识回答
   - 其他工具有结果 → 基于工具返回结果回答

3. **生成回答**
   - 确保回答完整、准确、有条理

## 可用工具

- `knowledge_base_search`: 从知识库搜索相关信息（RAG工具）
- 其他工具将根据系统决策动态推荐

## 回答规范

✓ 优先使用知识库内容，确保准确性
✓ 引用知识库信息时说明来源
✓ 未找到知识库信息时明确告知
✓ 避免在有知识库信息时使用通用知识
✓ 使用工具时说明选择理由
"""),
    MessagesPlaceholder(variable_name="chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# 创建默认智能体
if create_openai_tools_agent and AgentExecutor:
    # 使用旧版 langchain.agents
    agent = create_openai_tools_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=settings.max_iterations,
        handle_parsing_errors=True,
    )
else:
    # 使用新版 langgraph.prebuilt
    agent_executor = create_react_agent(llm, tools)


def create_dynamic_agent_executor(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
):
    """
    创建动态智能体执行器

    Args:
        model: 模型名称，如果为None则使用配置文件中的模型
        temperature: 温度参数
        max_tokens: 最大token数

    Returns:
        智能体执行器
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
    if create_openai_tools_agent and AgentExecutor:
        # 使用旧版 langchain.agents
        dynamic_agent = create_openai_tools_agent(dynamic_llm, current_tools, prompt)
        dynamic_executor = AgentExecutor(
            agent=dynamic_agent,
            tools=current_tools,
            verbose=True,
            max_iterations=settings.max_iterations,
            handle_parsing_errors=True,
        )
    else:
        # 使用新版 langgraph.prebuilt
        dynamic_executor = create_react_agent(dynamic_llm, current_tools)

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

