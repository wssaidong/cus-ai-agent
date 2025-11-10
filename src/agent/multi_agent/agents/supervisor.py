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
    监督者智能体 - Supervisor Pattern (增强版 - 支持用户引导)

    职责：
    1. 分析用户需求和对话历史
    2. 决定下一步行动：
       - 调用哪个 Worker Agent（search_agent, write_agent, analysis_agent, execution_agent）
       - 直接回答用户（respond）
       - 结束对话（finish）
    3. 为 Worker Agent 生成清晰的任务指令
    4. **主动引导用户**，提升用户体验：
       - 询问能力时：详细展示各 Worker 的能力和示例
       - 问题模糊时：主动询问澄清，提供选项
       - 超出范围时：友好告知限制，建议替代方案
       - 首次交互时：欢迎并简要介绍能力
       - 表达困惑时：提供具体使用建议

    Supervisor 模式优势：
    - 中央协调：统一管理多个专业化 Worker
    - 职责分离：每个 Worker 专注于特定领域
    - 易于扩展：添加新 Worker 无需修改现有逻辑
    - 灵活调度：根据任务类型动态选择最合适的 Worker
    - 用户引导：主动帮助用户更好地使用系统
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
            streaming=True,  # 启用流式输出
        )

        # 可用的 Worker Agents
        self.worker_names = worker_names or [
            "search_agent",      # 搜索智能体 - 负责知识库搜索
            "write_agent",       # 写入智能体 - 负责知识库写入
            "analysis_agent",    # 分析智能体 - 负责数据分析和推理
            "execution_agent",   # 执行智能体 - 负责调用 MCP 工具执行操作
            "quality_agent",     # 质量优化智能体 - 负责评估和优化回答质量
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
        """动态生成系统提示词"""
        # 为每个 Worker 生成描述（包含工具信息）
        workers_desc = "\n\n".join([
            self._get_worker_full_description(name)
            for name in self.worker_names
        ])

        # 动态生成示例
        prompt_examples = self._generate_prompt_examples()

        return f"""你是一个智能监督者（Supervisor），负责协调多个专业化的 Worker Agents 来完成用户任务。

【核心职责】
1. 分析用户的问题和需求
2. 查看对话历史，理解上下文
3. **基于每个 Worker 的工具能力**，决定调用哪个 Worker Agent 或直接回答
4. **主动引导用户**，帮助用户更好地使用系统能力

【可用的 Worker Agents 及其工具能力】
{workers_desc}

【用户引导策略】⭐ 新增

你需要在以下场景主动引导用户：

**场景1：用户询问能力时**
- 触发条件：用户问"你能做什么"、"有什么功能"、"怎么用"等
- 引导方式：详细介绍各 Worker 的能力，并提供具体示例问题
- 示例回答：展示各 Worker 的能力和具体示例问题，引导用户尝试

**场景2：问题模糊不清时**
- 触发条件：用户的问题缺少关键信息，无法准确判断意图
- 引导方式：主动询问澄清，提供选项帮助用户明确需求
- 示例：
  用户："帮我查一下"
  回答："我可以帮你查询信息。请问你想：
  1. 📚 搜索知识库中的内容？
  2. 📊 查询系统日志或数据？
  3. 🔍 分析某个问题？
  请告诉我具体想查什么，我会为你找到最合适的方式。"

**场景3：超出能力范围时**
- 触发条件：用户请求的功能当前 Worker 都无法完成
- 引导方式：明确告知限制，建议替代方案或相关功能
- 示例：
  用户："帮我订个外卖"
  回答："抱歉，我目前还不能帮你订外卖。我的专长是：
  - 📚 知识库搜索和管理
  - 🔍 数据分析和推理
  - ⚙️ 系统工具调用（日志查询、消息发送等）

  如果你有这些方面的需求，我很乐意帮助你！"

**场景4：首次交互时**
- 触发条件：这是用户的第一条消息（对话历史为空或只有问候）
- 引导方式：友好欢迎，简要介绍能力，鼓励尝试
- 示例：
  用户："你好"
  回答："你好！我是智能助手，可以帮你：
  📚 搜索知识库  ✍️ 管理知识  🔍 分析数据  ⚙️ 执行工具

  你可以试试问我一些问题，我会帮你找到最合适的方式！"

**场景5：用户表达困惑时**
- 触发条件：用户说"不知道"、"不太明白"、"怎么办"等
- 引导方式：提供具体的使用建议和示例
- 示例：提供 2-3 个相关的示例问题，引导用户尝试

【决策规则】

⚠️ **重要：每个用户请求只调用一次 Worker Agent**
- Worker Agent 完成任务后会直接返回结果给用户
- 不要重复调用同一个 Worker
- 一次对话只需要一个决策

⚠️ **重要：基于工具能力做决策**
- 查看每个 Worker 的可用工具
- 如果 Worker 没有合适的工具，不要调用它
- 选择工具最匹配用户需求的 Worker

⚠️ **重要：优先引导而非拒绝**
- 遇到模糊问题时，主动询问澄清
- 遇到超出范围的请求，建议相关功能
- 保持友好、耐心、专业的态度

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

**情况2：直接回答（next_agent: respond）** ⭐ 增强
当满足以下条件时，选择 respond：
- 简单的问候、闲聊
- 询问你的能力或功能 → **需要详细介绍能力并提供示例**
- 不需要工具就能回答的常识性问题
- 澄清性问题
- 问题模糊需要引导 → **主动询问澄清，提供选项**
- 超出能力范围 → **明确告知限制，建议替代方案**
- 用户表达困惑 → **提供具体使用建议和示例**

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
✅ {{"next_agent": "worker_name", "task_instruction": "...", "reasoning": "..."}}

【示例】

{prompt_examples}

【注意事项】
1. ⚠️ **每个用户请求只调用一次 Worker** - Worker 会完成任务并直接回答用户
2. ⚠️ **主动引导用户** - 遇到模糊问题或超出范围时，提供清晰的引导和建议
3. 仔细阅读对话历史，理解上下文
4. 准确判断用户意图，选择最合适的 Worker
5. 生成的任务指令要清晰、具体、友好
6. 输出必须是有效的 JSON 格式
7. 保持专业、友好、耐心的态度
8. 如果不确定，优先询问澄清而非猜测
9. **不要重复调用同一个 Worker** - 每个 Worker 只需要调用一次
"""

    def _get_worker_description(self, worker_name: str) -> str:
        """
        动态获取 Worker 的简短描述

        基于 Worker 名称和工具能力动态生成描述

        Args:
            worker_name: Worker 名称

        Returns:
            str: Worker 的简短描述
        """
        # 预定义的描述（优先使用）
        predefined_descriptions = {
            "search_agent": "负责搜索知识库，查询相关信息",
            "write_agent": "负责写入、更新、删除知识库内容",
            "analysis_agent": "负责数据分析、推理、计算等复杂任务",
            "execution_agent": "负责调用 MCP 工具执行各种操作（日志查询、消息发送、网络测试、数据库查询等）",
            "quality_agent": "负责评估和优化智能体回答的质量（准确性、相关性、完整性、清晰度、有用性）",
        }

        # 如果有预定义描述，使用它
        if worker_name in predefined_descriptions:
            return predefined_descriptions[worker_name]

        # 否则，基于工具动态生成描述
        tools = self.worker_tools.get(worker_name, [])
        if tools:
            tool_names = [tool.name if hasattr(tool, 'name') else str(tool) for tool in tools[:3]]
            return f"负责执行相关操作（{', '.join(tool_names)}等）"

        # 最后的默认描述
        return "专业化的工作智能体"

    def _get_example_questions(self) -> Dict[str, List[str]]:
        """
        动态生成每个 Worker 的示例问题

        基于 Worker 的工具能力动态生成示例问题，支持 Agent 的增减

        Returns:
            Dict[str, List[str]]: Worker 名称到示例问题列表的映射
        """
        # 默认示例问题模板（当无法从工具推断时使用）
        default_examples = {
            "search_agent": [
                "MGW网关的配置方法是什么？",
                "查询一下关于Python异步编程的知识",
                "搜索微服务架构的最佳实践",
            ],
            "write_agent": [
                "帮我添加一条知识：Docker容器的基本命令",
                "更新知识库中关于Redis的配置信息",
                "删除过时的API文档",
            ],
            "analysis_agent": [
                "分析一下微服务架构和单体架构的优缺点",
                "对比MySQL和PostgreSQL的性能差异",
                "计算一下这个算法的时间复杂度",
            ],
            "execution_agent": [
                "查询网关的最新日志",
                "发送一条美信消息通知团队",
                "测试数据库连接是否正常",
            ],
            "quality_agent": [
                "评估一下上一个回答的质量",
                "优化改进刚才的回答",
                "这个回答质量怎么样？",
            ],
        }

        examples = {}

        # 为每个 Worker 动态生成示例
        for worker_name in self.worker_names:
            tools = self.worker_tools.get(worker_name, [])

            if not tools:
                # 没有工具，使用默认示例或生成通用示例
                examples[worker_name] = default_examples.get(worker_name, [
                    f"使用 {worker_name} 处理相关任务"
                ])
            else:
                # 基于工具生成示例问题
                worker_examples = []

                # 从工具描述中提取示例（最多3个）
                for tool in tools[:3]:
                    tool_desc = tool.description if hasattr(tool, 'description') else str(tool)
                    # 生成基于工具的示例问题
                    if "搜索" in tool_desc or "search" in tool_desc.lower():
                        worker_examples.append(f"搜索相关信息")
                    elif "添加" in tool_desc or "add" in tool_desc.lower():
                        worker_examples.append(f"添加新的内容")
                    elif "查询" in tool_desc or "query" in tool_desc.lower():
                        worker_examples.append(f"查询相关数据")
                    elif "分析" in tool_desc or "analyze" in tool_desc.lower():
                        worker_examples.append(f"分析数据或问题")
                    else:
                        # 使用工具名称生成示例
                        worker_examples.append(f"使用 {tool.name if hasattr(tool, 'name') else '工具'}")

                # 如果没有生成示例，使用默认的
                if not worker_examples:
                    worker_examples = default_examples.get(worker_name, [
                        f"使用 {worker_name} 处理任务"
                    ])

                examples[worker_name] = worker_examples

        return examples

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

    def _generate_prompt_examples(self) -> str:
        """
        动态生成 system prompt 中的示例部分

        基于当前可用的 Worker 动态生成示例，支持 Agent 的增减

        Returns:
            str: 示例部分的文本
        """
        example_questions = self._get_example_questions()

        examples = []

        # 为前3个 Worker 生成调用示例
        for i, worker_name in enumerate(self.worker_names[:3], 1):
            desc = self._get_worker_description(worker_name)
            worker_examples = example_questions.get(worker_name, [f"使用 {worker_name}"])
            example_question = worker_examples[0] if worker_examples else f"使用 {worker_name}"

            # 生成友好的标题
            title = worker_name.replace("_", " ").title()

            examples.append(f"""示例{i} - 调用{title}：
用户: "{example_question}"
输出:
```json
{{{{
  "next_agent": "{worker_name}",
  "task_instruction": "根据用户需求执行相应任务",
  "reasoning": "用户需要{desc}"
}}}}
```""")

        # 添加引导示例
        welcome_msg = self._generate_welcome_message().replace('\n', '\\n')
        examples.append(f"""示例{len(examples)+1} - 首次问候（引导用户）⭐ 新增：
用户: "你好"
输出:
```json
{{{{
  "next_agent": "respond",
  "task_instruction": "{welcome_msg}",
  "reasoning": "首次问候，需要友好欢迎并简要介绍能力，引导用户尝试"
}}}}
```""")

        capability_intro = self._generate_capability_introduction().replace('\n', '\\n')
        examples.append(f"""示例{len(examples)+1} - 询问能力（详细展示）⭐ 新增：
用户: "你能做什么？"
输出:
```json
{{{{
  "next_agent": "respond",
  "task_instruction": "{capability_intro}",
  "reasoning": "用户询问能力，需要详细介绍各 Worker 的能力并提供具体示例"
}}}}
```""")

        clarification = self._generate_clarification_prompt("").replace('\n', '\\n')
        examples.append(f"""示例{len(examples)+1} - 问题模糊（主动澄清）⭐ 新增：
用户: "帮我查一下"
输出:
```json
{{{{
  "next_agent": "respond",
  "task_instruction": "{clarification}",
  "reasoning": "用户问题模糊，缺少关键信息，需要主动询问澄清"
}}}}
```""")

        out_of_scope = self._generate_out_of_scope_response("").replace('\n', '\\n')
        examples.append(f"""示例{len(examples)+1} - 超出范围（建议替代）⭐ 新增：
用户: "帮我订个外卖"
输出:
```json
{{{{
  "next_agent": "respond",
  "task_instruction": "{out_of_scope}",
  "reasoning": "用户请求超出能力范围，需要明确告知限制并建议相关功能"
}}}}
```""")

        examples.append(f"""示例{len(examples)+1} - 任务完成：
用户: "好的，谢谢"
输出:
```json
{{{{
  "next_agent": "finish",
  "task_instruction": "不客气！如果还有其他问题，随时找我。",
  "reasoning": "用户表示感谢，对话可以结束"
}}}}
```""")

        return "\n\n".join(examples)

    def _generate_capability_introduction(self) -> str:
        """
        动态生成能力介绍文本

        基于当前可用的 Worker 动态生成介绍，支持 Agent 的增减

        Returns:
            str: 详细的能力介绍文本
        """
        example_questions = self._get_example_questions()

        intro = "我可以帮你完成以下任务：\n\n"

        # 动态生成每个 Worker 的图标和标题
        worker_icons = {
            "search": "📚",
            "write": "✍️",
            "analysis": "🔍",
            "execution": "⚙️",
            "query": "🔎",
            "manage": "📝",
            "process": "⚡",
            "monitor": "👁️",
        }

        parts = []
        for worker_name in self.worker_names:
            # 动态确定图标
            icon = "🤖"  # 默认图标
            for key, emoji in worker_icons.items():
                if key in worker_name.lower():
                    icon = emoji
                    break

            # 获取 Worker 描述
            desc = self._get_worker_description(worker_name)

            # 生成友好的标题
            title = worker_name.replace("_", " ").title()

            # 获取示例
            examples = example_questions.get(worker_name, [])
            example_text = f"- 示例：{examples[0]}" if examples else ""

            parts.append(f"{icon} **{title}**\n- {desc}\n{example_text}")

        intro += "\n\n".join(parts)
        intro += "\n\n你想尝试哪个功能？"

        return intro

    def _generate_clarification_prompt(self, user_message: str) -> str:
        """
        生成澄清提示

        当用户问题模糊时，生成引导性的澄清问题

        Args:
            user_message: 用户的原始消息

        Returns:
            str: 澄清提示文本
        """
        return """我可以帮你查询信息。请问你想：
1. 📚 搜索知识库中的内容？
2. 📊 查询系统日志或数据？
3. 🔍 分析某个问题？

请告诉我具体想查什么，我会为你找到最合适的方式。"""

    def _generate_out_of_scope_response(self, user_message: str) -> str:
        """
        生成超出范围的回复

        当用户请求超出系统能力时，友好地告知限制并建议替代方案

        Args:
            user_message: 用户的原始消息

        Returns:
            str: 超出范围的回复文本
        """
        return """抱歉，这个请求可能超出了我目前的能力范围。

我的专长是：
- 📚 知识库搜索和管理
- 🔍 数据分析和推理
- ⚙️ 系统工具调用（日志查询、消息发送、网络测试等）

如果你有这些方面的需求，我很乐意帮助你！你也可以问我"你能做什么"来了解更多功能。"""

    def _generate_welcome_message(self) -> str:
        """
        动态生成欢迎消息

        基于当前可用的 Worker 动态生成欢迎消息，支持 Agent 的增减

        Returns:
            str: 欢迎消息文本
        """
        example_questions = self._get_example_questions()

        # 动态生成能力简介
        capabilities = []
        worker_icons = {
            "search": "📚",
            "write": "✍️",
            "analysis": "🔍",
            "execution": "⚙️",
            "query": "🔎",
            "manage": "📝",
        }

        for worker_name in self.worker_names[:4]:  # 最多显示4个
            icon = "🤖"
            for key, emoji in worker_icons.items():
                if key in worker_name.lower():
                    icon = emoji
                    break

            # 简化的能力描述
            simple_desc = worker_name.replace("_agent", "").replace("_", " ").title()
            capabilities.append(f"{icon} {simple_desc}")

        capabilities_text = "  ".join(capabilities)

        # 获取第一个示例问题
        first_example = "搜索相关信息"
        if self.worker_names and self.worker_names[0] in example_questions:
            examples = example_questions[self.worker_names[0]]
            if examples:
                first_example = examples[0]

        return f"""你好！我是智能助手，可以帮你：
{capabilities_text}

你可以试试问我："{first_example}"
或者告诉我你想做什么，我会帮你找到最合适的方式！"""

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
        messages = state.get("messages", [])

        # 构建提示
        prompt_messages = [
            SystemMessage(content=self.system_prompt),
        ]

        # 添加对话历史（最近10条）
        # 过滤掉空消息，避免 "content len should not be 0" 错误
        recent_messages = messages[-10:] if len(messages) > 10 else messages
        for msg in recent_messages:
            # 检查消息内容是否为空
            if hasattr(msg, 'content') and msg.content and msg.content.strip():
                prompt_messages.append(msg)
            else:
                app_logger.warning(f"[{self.name}] 跳过空消息: {type(msg).__name__}")

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

