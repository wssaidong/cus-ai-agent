"""
API数据模型
"""
from typing import Optional, Dict, Any, List, Literal, Union
from pydantic import BaseModel, Field
import time


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., description="用户消息", min_length=1)
    session_id: Optional[str] = Field(None, description="会话ID")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="配置参数")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "帮我计算 123 + 456",
                "session_id": "user-123",
                "config": {
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
            }
        }


class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str = Field(..., description="智能体响应")
    session_id: Optional[str] = Field(None, description="会话ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "response": "123 + 456 = 579",
                "session_id": "user-123",
                "metadata": {
                    "tool_calls": 1,
                    "llm_calls": 1,
                    "execution_time": 1.23
                }
            }
        }


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="版本号")
    timestamp: str = Field(..., description="时间戳")




# ==================== OpenAI 兼容模型 ====================

class Message(BaseModel):
    """消息模型"""
    role: Literal["system", "user", "assistant", "function"] = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    name: Optional[str] = Field(None, description="消息发送者名称")
    function_call: Optional[Dict[str, Any]] = Field(None, description="函数调用信息")


class CompletionRequest(BaseModel):
    """Completions请求模型（OpenAI兼容，使用多智能体架构）"""
    model: str = Field(default="gpt-4-turbo-preview", description="模型名称")
    messages: List[Message] = Field(..., description="消息列表", min_length=1)
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2, description="温度参数")
    max_tokens: Optional[int] = Field(default=2000, ge=1, description="最大token数")
    top_p: Optional[float] = Field(default=1.0, ge=0, le=1, description="核采样参数")
    n: Optional[int] = Field(default=1, ge=1, le=10, description="生成数量")
    stream: Optional[bool] = Field(default=False, description="是否流式输出")
    stop: Optional[Union[str, List[str]]] = Field(None, description="停止词")
    presence_penalty: Optional[float] = Field(default=0, ge=-2, le=2, description="存在惩罚")
    frequency_penalty: Optional[float] = Field(default=0, ge=-2, le=2, description="频率惩罚")
    user: Optional[str] = Field(None, description="用户标识")

    class Config:
        json_schema_extra = {
            "example": {
                "model": "gpt-4-turbo-preview",
                "messages": [
                    {"role": "system", "content": "你是一个智能助手"},
                    {"role": "user", "content": "帮我计算 123 + 456"}
                ],
                "temperature": 0.7,
                "max_tokens": 2000,
                "stream": False
            }
        }


class CompletionChoice(BaseModel):
    """Completion选择项"""
    index: int = Field(..., description="选择索引")
    message: Message = Field(..., description="消息内容")
    finish_reason: Optional[str] = Field(None, description="结束原因: stop, length, function_call, content_filter")


class CompletionUsage(BaseModel):
    """Token使用统计"""
    prompt_tokens: int = Field(..., description="提示词token数")
    completion_tokens: int = Field(..., description="生成token数")
    total_tokens: int = Field(..., description="总token数")


class CompletionResponse(BaseModel):
    """Completions响应模型（OpenAI兼容）"""
    id: str = Field(..., description="响应ID")
    object: str = Field(default="chat.completion", description="对象类型")
    created: int = Field(..., description="创建时间戳")
    model: str = Field(..., description="使用的模型")
    choices: List[CompletionChoice] = Field(..., description="生成的选择列表")
    usage: CompletionUsage = Field(..., description="Token使用统计")
    system_fingerprint: Optional[str] = Field(None, description="系统指纹")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "chatcmpl-123",
                "object": "chat.completion",
                "created": 1677652288,
                "model": "gpt-4-turbo-preview",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "123 + 456 = 579"
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": 20,
                    "completion_tokens": 10,
                    "total_tokens": 30
                }
            }
        }


class CompletionStreamChunk(BaseModel):
    """流式响应块（OpenAI兼容）"""
    id: str = Field(..., description="响应ID")
    object: str = Field(default="chat.completion.chunk", description="对象类型")
    created: int = Field(..., description="创建时间戳")
    model: str = Field(..., description="使用的模型")
    choices: List[Dict[str, Any]] = Field(..., description="增量选择列表")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "chatcmpl-123",
                "object": "chat.completion.chunk",
                "created": 1677652288,
                "model": "gpt-4-turbo-preview",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "role": "assistant",
                            "content": "123"
                        },
                        "finish_reason": None
                    }
                ]
            }
        }

