"""
Planner 智能体 - 规划者

负责分析用户需求，决定下一步行动
"""
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.config import settings
from src.utils import app_logger
from src.agent.multi_agent.chat_state import ChatState


class PlannerAgent:
    """
    规划者智能体
    
    职责：
    1. 分析用户需求和对话历史
    2. 决定下一步行动：
       - execute: 需要调用执行者完成任务
       - respond: 可以直接回答用户
       - finish: 任务已完成
    3. 为执行者生成清晰的执行指令
    """
    
    def __init__(self, llm: ChatOpenAI = None):
        """初始化规划者"""
        self.name = "Planner"
        self.llm = llm or ChatOpenAI(
            model=settings.model_name,
            temperature=0.3,  # 较低温度，保持规划的一致性
            max_tokens=settings.max_tokens,
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_api_base,
        )
        
        self.system_prompt = self._get_system_prompt()
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一个智能规划者（Planner），负责分析用户需求并决定下一步行动。

【核心职责】
1. 分析用户的问题和需求
2. 查看对话历史，理解上下文
3. 决定下一步行动

【决策规则】

**情况1：需要执行任务 (next_action: execute)**
当用户需求满足以下条件时，选择 execute：
- 需要搜索知识库信息
- 需要写入或更新知识库
- 需要执行具体的操作任务
- 需要调用工具完成任务

此时你需要生成清晰的 execution_instruction，告诉执行者要做什么。

**情况2：直接回答 (next_action: respond)**
当用户需求满足以下条件时，选择 respond：
- 简单的问候、闲聊
- 询问你的能力或功能
- 不需要工具就能回答的常识性问题
- 澄清性问题

此时你需要在 execution_instruction 中写上你的回答内容。

**情况3：任务完成 (next_action: finish)**
当满足以下条件时，选择 finish：
- 用户明确表示结束对话（如"再见"、"谢谢"等）
- 任务已经完成且用户满意

【输出格式】
你必须严格按照以下 JSON 格式输出：

```json
{
  "next_action": "execute|respond|finish",
  "execution_instruction": "具体指令或回答内容",
  "reasoning": "决策理由"
}
```

【示例】

示例1 - 需要搜索知识库：
用户: "MGW网关的配置方法是什么？"
输出:
```json
{
  "next_action": "execute",
  "execution_instruction": "搜索知识库中关于MGW网关配置方法的信息，并整理成清晰的步骤",
  "reasoning": "用户询问具体的技术配置方法，需要从知识库中搜索相关信息"
}
```

示例2 - 直接回答：
用户: "你好"
输出:
```json
{
  "next_action": "respond",
  "execution_instruction": "你好！我是智能助手，可以帮你搜索知识库、回答问题。有什么我可以帮助你的吗？",
  "reasoning": "简单的问候，不需要调用工具，直接回答即可"
}
```

示例3 - 任务完成：
用户: "好的，谢谢"
输出:
```json
{
  "next_action": "finish",
  "execution_instruction": "不客气！如果还有其他问题，随时找我。",
  "reasoning": "用户表示感谢，对话可以结束"
}
```

【注意事项】
1. 仔细阅读对话历史，理解上下文
2. 准确判断用户意图
3. 生成的指令要清晰、具体
4. 输出必须是有效的 JSON 格式
5. 保持专业、友好的态度
"""
    
    async def plan(self, state: ChatState) -> Dict[str, Any]:
        """
        分析需求并制定计划
        
        Args:
            state: 当前聊天状态
        
        Returns:
            更新后的状态字段
        """
        app_logger.info(f"[{self.name}] 开始分析需求...")
        
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
                # 尝试直接解析
                json_str = response_text.strip()
            
            plan = json.loads(json_str)
            
            next_action = plan.get("next_action", "respond")
            execution_instruction = plan.get("execution_instruction", "")
            reasoning = plan.get("reasoning", "")
            
            app_logger.info(f"[{self.name}] 决策完成:")
            app_logger.info(f"  - 下一步行动: {next_action}")
            app_logger.info(f"  - 执行指令: {execution_instruction[:100]}...")
            app_logger.info(f"  - 决策理由: {reasoning}")
            
            # 返回更新的状态字段
            return {
                "next_action": next_action,
                "execution_instruction": execution_instruction,
            }
            
        except Exception as e:
            app_logger.error(f"[{self.name}] 规划失败: {e}")
            # 默认直接回答
            return {
                "next_action": "respond",
                "execution_instruction": "抱歉，我在处理你的请求时遇到了问题。请重新描述你的需求。",
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

