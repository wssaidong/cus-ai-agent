"""
SupervisorAgent - 监督者智能体

负责分析用户需求，决定调用哪个 Worker Agent 来完成任务
"""
from typing import Dict, Any, List, Literal, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import BaseTool
from src.config import settings
from src.utils import app_logger
from src.agent.multi_agent.chat_state import ChatState


class SupervisorAgent:
    """
    监督者智能体 - Supervisor Pattern

    职责：
    1. 分析用户需求和对话历史
    2. 决定下一步行动：
       - 调用哪个 Worker Agent（search_agent, write_agent, analysis_agent）
       - 直接回答用户（respond）
       - 结束对话（finish）
    3. 为 Worker Agent 生成清晰的任务指令

    Supervisor 模式优势：
    - 中央协调：统一管理多个专业化 Worker
    - 职责分离：每个 Worker 专注于特定领域
    - 易于扩展：添加新 Worker 无需修改现有逻辑
    - 灵活调度：根据任务类型动态选择最合适的 Worker
    """

    def __init__(
        self,
        llm: ChatOpenAI = None,
        worker_names: List[str] = None,
        worker_tools: Optional[Dict[str, List[BaseTool]]] = None
    ):
        """
        初始化监督者

        Args:
            llm: 语言模型实例
            worker_names: 可用的 Worker Agent 名称列表
            worker_tools: 每个 Worker 的工具映射 {"worker_name": [tools]}
        """
        self.name = "Supervisor"
        self.llm = llm or ChatOpenAI(
            model=settings.model_name,
            temperature=0.2,  # 低温度，保持决策的一致性和准确性
            max_tokens=settings.max_tokens,
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_api_base,
            model_kwargs={
                "response_format": {"type": "json_object"}  # 强制 JSON 输出
            }
        )

        # 可用的 Worker Agents
        self.worker_names = worker_names or [
            "search_agent",      # 搜索智能体 - 负责知识库搜索
            "write_agent",       # 写入智能体 - 负责知识库写入
            "analysis_agent",    # 分析智能体 - 负责数据分析和推理
            "execution_agent",   # 执行智能体 - 负责调用 MCP 工具执行操作
        ]

        # Worker 工具映射
        self.worker_tools = worker_tools or {}

        self.system_prompt = self._get_system_prompt()

        app_logger.info(f"[{self.name}] 初始化完成，管理 {len(self.worker_names)} 个 Worker Agents")
        app_logger.info(f"[{self.name}] Workers: {', '.join(self.worker_names)}")

        # 打印每个 Worker 的工具信息
        for worker_name in self.worker_names:
            tools = self.worker_tools.get(worker_name, [])
            app_logger.info(f"[{self.name}] {worker_name} 有 {len(tools)} 个工具: {[t.name for t in tools]}")

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        # 为每个 Worker 生成描述（包含工具信息）
        workers_desc = "\n\n".join([
            self._get_worker_full_description(name)
            for name in self.worker_names
        ])

        return f"""你是一个智能监督者（Supervisor），负责协调多个专业化的 Worker Agents 来完成用户任务。

【核心职责】
1. 分析用户的问题和需求
2. 查看对话历史，理解上下文
3. **基于每个 Worker 的工具能力**，决定调用哪个 Worker Agent 或直接回答

【可用的 Worker Agents 及其工具能力】
{workers_desc}

【决策规则】

⚠️ **重要：每个用户请求只调用一次 Worker Agent**
- Worker Agent 完成任务后会直接返回结果给用户
- 不要重复调用同一个 Worker
- 一次对话只需要一个决策

⚠️ **重要：基于工具能力做决策**
- 查看每个 Worker 的可用工具
- 如果 Worker 没有合适的工具，不要调用它
- 选择工具最匹配用户需求的 Worker

**情况1：调用 Worker Agent（一次性任务）**
根据任务类型和工具能力选择合适的 Worker，Worker 会完成任务并直接回答用户：

- **search_agent**: 当需要搜索知识库、查询信息时
  示例：用户询问"MGW网关的配置方法是什么？"
  注意：search_agent 会搜索并直接回答用户，不需要再次调用

- **write_agent**: 当需要写入、更新、删除知识库内容时
  示例：用户说"帮我添加一条关于XXX的知识"
  注意：write_agent 会完成写入并直接回答用户，不需要再次调用

- **analysis_agent**: 当需要分析数据、推理、计算时
  示例：用户问"分析一下这两个方案的优劣"
  注意：analysis_agent 会完成分析并直接回答用户，不需要再次调用

- **execution_agent**: 当需要调用 MCP 工具执行操作时
  示例：用户问"查询网关日志"、"发送美信消息"、"测试网络连通性"
  注意：execution_agent 会调用工具并直接回答用户，不需要再次调用

**情况2：直接回答（next_agent: respond）**
当满足以下条件时，选择 respond：
- 简单的问候、闲聊
- 询问你的能力或功能
- 不需要工具就能回答的常识性问题
- 澄清性问题

**情况3：任务完成（next_agent: finish）**
当满足以下条件时，选择 finish：
- 用户明确表示结束对话（如"再见"、"谢谢"等）
- 任务已经完成且用户满意

【输出格式】
⚠️ **极其重要：你必须只输出 JSON，不要输出任何其他文本！**

你的输出必须是一个有效的 JSON 对象，格式如下：

{{
  "next_agent": "search_agent|write_agent|analysis_agent|execution_agent|respond|finish",
  "task_instruction": "给 Worker Agent 的具体任务指令或回答内容",
  "reasoning": "决策理由"
}}

**禁止的输出示例：**
❌ "查询网关日志数据..."（纯文本，不是 JSON）
❌ "让我帮你查询..." {{...}}（JSON 前有文本）
❌ 任何不是 JSON 对象的输出

**正确的输出示例：**
✅ {{"next_agent": "search_agent", "task_instruction": "...", "reasoning": "..."}}

【示例】

示例1 - 调用搜索智能体：
用户: "MGW网关的配置方法是什么？"
输出:
```json
{{
  "next_agent": "search_agent",
  "task_instruction": "搜索知识库中关于MGW网关配置方法的信息，并整理成清晰的步骤",
  "reasoning": "用户询问具体的技术配置方法，需要从知识库中搜索相关信息"
}}
```

示例2 - 调用写入智能体：
用户: "帮我添加一条知识：Python的列表推导式语法是[x for x in iterable]"
输出:
```json
{{
  "next_agent": "write_agent",
  "task_instruction": "将关于Python列表推导式的知识添加到知识库：语法是[x for x in iterable]",
  "reasoning": "用户明确要求添加知识到知识库，需要调用写入智能体"
}}
```

示例3 - 调用分析智能体：
用户: "分析一下微服务架构和单体架构的优缺点"
输出:
```json
{{
  "next_agent": "analysis_agent",
  "task_instruction": "分析微服务架构和单体架构的优缺点，从性能、可维护性、部署复杂度等多个维度进行对比",
  "reasoning": "用户需要进行架构对比分析，这是分析智能体的专长"
}}
```

示例4 - 直接回答：
用户: "你好"
输出:
```json
{{
  "next_agent": "respond",
  "task_instruction": "你好！我是智能助手，可以帮你搜索知识库、添加知识、分析问题。有什么我可以帮助你的吗？",
  "reasoning": "简单的问候，不需要调用 Worker Agent，直接回答即可"
}}
```

示例5 - 任务完成：
用户: "好的，谢谢"
输出:
```json
{{
  "next_agent": "finish",
  "task_instruction": "不客气！如果还有其他问题，随时找我。",
  "reasoning": "用户表示感谢，对话可以结束"
}}
```

【注意事项】
1. ⚠️ **每个用户请求只调用一次 Worker** - Worker 会完成任务并直接回答用户
2. 仔细阅读对话历史，理解上下文
3. 准确判断用户意图，选择最合适的 Worker
4. 生成的任务指令要清晰、具体
5. 输出必须是有效的 JSON 格式
6. 保持专业、友好的态度
7. 如果不确定，优先选择 search_agent 搜索相关信息
8. **不要重复调用同一个 Worker** - 每个 Worker 只需要调用一次
"""

    def _get_worker_description(self, worker_name: str) -> str:
        """获取 Worker 的简短描述"""
        descriptions = {
            "search_agent": "负责搜索知识库，查询相关信息",
            "write_agent": "负责写入、更新、删除知识库内容",
            "analysis_agent": "负责数据分析、推理、计算等复杂任务",
            "execution_agent": "负责调用 MCP 工具执行各种操作（日志查询、消息发送、网络测试、数据库查询等）",
        }
        return descriptions.get(worker_name, "专业化的工作智能体")

    def _get_worker_full_description(self, worker_name: str) -> str:
        """获取 Worker 的完整描述（包含工具信息）"""
        base_desc = self._get_worker_description(worker_name)
        tools = self.worker_tools.get(worker_name, [])

        if not tools:
            return f"- **{worker_name}**: {base_desc}\n  ⚠️ 当前没有可用工具"

        # 生成工具列表
        tools_desc = "\n  ".join([
            f"• {tool.name}: {tool.description[:80]}..." if len(tool.description) > 80 else f"• {tool.name}: {tool.description}"
            for tool in tools
        ])

        return f"""- **{worker_name}**: {base_desc}
  可用工具 ({len(tools)} 个):
  {tools_desc}"""

    async def supervise(self, state: ChatState) -> Dict[str, Any]:
        """
        监督和调度任务

        Args:
            state: 当前聊天状态

        Returns:
            更新后的状态字段
        """
        app_logger.info(f"[{self.name}] 开始分析任务...")

        # 获取消息历史
        messages = state["messages"]

        # 构建提示
        prompt_messages = [
            SystemMessage(content=self.system_prompt),
        ]

        # 添加对话历史（最近10条）
        recent_messages = messages[-10:] if len(messages) > 10 else messages
        prompt_messages.extend(recent_messages)

        # 记录提示
        self._log_prompt(prompt_messages)

        # 调用 LLM
        try:
            response = await self.llm.ainvoke(prompt_messages)
            response_text = response.content

            # 记录响应
            self._log_response(response_text)

            # 解析响应
            import json
            import re

            # 提取 JSON（可能被包裹在 ```json ``` 中）
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试查找任何 JSON 对象
                json_match = re.search(r'\{.*?\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    # 没有找到 JSON，记录原始响应
                    app_logger.error(f"[{self.name}] 无法从响应中提取 JSON")
                    app_logger.error(f"[{self.name}] 原始响应: {response_text[:500]}")
                    raise ValueError("响应中没有有效的 JSON 格式")

            # 尝试解析 JSON
            try:
                decision = json.loads(json_str)
            except json.JSONDecodeError as je:
                app_logger.error(f"[{self.name}] JSON 解析失败: {je}")
                app_logger.error(f"[{self.name}] 尝试解析的内容: {json_str[:500]}")
                raise

            next_agent = decision.get("next_agent", "respond")
            task_instruction = decision.get("task_instruction", "")
            reasoning = decision.get("reasoning", "")

            app_logger.info(f"[{self.name}] 调度决策完成:")
            app_logger.info(f"  - 下一个 Agent: {next_agent}")
            app_logger.info(f"  - 任务指令: {task_instruction[:100]}...")
            app_logger.info(f"  - 决策理由: {reasoning}")

            # 返回更新的状态字段
            return {
                "next_agent": next_agent,
                "task_instruction": task_instruction,
            }

        except Exception as e:
            app_logger.error(f"[{self.name}] 调度失败: {e}")
            app_logger.error(f"[{self.name}] 错误类型: {type(e).__name__}")
            import traceback
            app_logger.error(f"[{self.name}] 堆栈跟踪:\n{traceback.format_exc()}")

            # 默认直接回答
            return {
                "next_agent": "respond",
                "task_instruction": "抱歉，我在处理你的请求时遇到了问题。请重新描述你的需求。",
            }

    def _log_prompt(self, messages):
        """记录提示"""
        app_logger.info(f"[{self.name}] 发送提示 (消息数: {len(messages)})")
        for i, msg in enumerate(messages):
            msg_type = msg.__class__.__name__
            content_preview = msg.content[:100] if len(msg.content) > 100 else msg.content
            app_logger.debug(f"  [{i+1}] {msg_type}: {content_preview}...")

    def _log_response(self, response: str):
        """记录响应"""
        preview = response[:200] if len(response) > 200 else response
        app_logger.info(f"[{self.name}] 收到响应: {preview}...")

