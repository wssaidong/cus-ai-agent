"""
工具名称验证和清理模块

用于验证和清理工具名称，确保符合 OpenAI API 的函数名称规范：
- 只允许 a-z, A-Z, 0-9, 中文字符, 下划线和破折号
- 最长 64 字符
- 不能以数字开头
"""

import re
from typing import Tuple
from src.utils import app_logger


# OpenAI 函数名称规范
OPENAI_FUNCTION_NAME_PATTERN = r'^[a-zA-Z0-9_\-\u4e00-\u9fff]+$'
MAX_FUNCTION_NAME_LENGTH = 64


def is_valid_function_name(name: str) -> bool:
    """
    检查函数名称是否符合 OpenAI API 规范
    
    Args:
        name: 函数名称
        
    Returns:
        True 如果有效，False 否则
    """
    if not name or len(name) > MAX_FUNCTION_NAME_LENGTH:
        return False
    
    # 检查是否只包含允许的字符
    if not re.match(OPENAI_FUNCTION_NAME_PATTERN, name):
        return False
    
    # 检查是否以数字开头
    if name[0].isdigit():
        return False
    
    return True


def clean_function_name(name: str, max_length: int = MAX_FUNCTION_NAME_LENGTH) -> str:
    """
    清理函数名称，使其符合 OpenAI API 规范
    
    清理规则：
    1. 移除所有不允许的字符（保留中文、英文、数字、下划线、破折号）
    2. 如果以数字开头，添加前缀
    3. 截断到最大长度
    
    Args:
        name: 原始函数名称
        max_length: 最大长度（默认 64）
        
    Returns:
        清理后的函数名称
    """
    if not name:
        return "tool"
    
    # 移除不允许的字符，保留中文、英文、数字、下划线、破折号
    # 使用正则表达式替换不允许的字符为下划线
    cleaned = re.sub(r'[^\w\-\u4e00-\u9fff]', '_', name, flags=re.UNICODE)
    
    # 移除连续的下划线
    cleaned = re.sub(r'_+', '_', cleaned)
    
    # 移除前后的下划线
    cleaned = cleaned.strip('_')
    
    # 如果以数字开头，添加前缀
    if cleaned and cleaned[0].isdigit():
        cleaned = f"tool_{cleaned}"
    
    # 如果为空，使用默认名称
    if not cleaned:
        cleaned = "tool"
    
    # 截断到最大长度
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    
    return cleaned


def validate_and_clean_tool_name(original_name: str) -> Tuple[str, bool]:
    """
    验证和清理工具名称
    
    Args:
        original_name: 原始工具名称
        
    Returns:
        (清理后的名称, 是否需要清理)
    """
    if is_valid_function_name(original_name):
        return original_name, False
    
    cleaned_name = clean_function_name(original_name)
    
    # 再次验证清理后的名称
    if not is_valid_function_name(cleaned_name):
        app_logger.warning(
            f"清理后的工具名称仍然无效: {original_name} -> {cleaned_name}"
        )
    
    return cleaned_name, True


def sanitize_tool_names(tools: list) -> list:
    """
    清理工具列表中的所有工具名称
    
    Args:
        tools: LangChain 工具列表
        
    Returns:
        清理后的工具列表
    """
    sanitized_tools = []
    
    for tool in tools:
        original_name = tool.name
        cleaned_name, was_cleaned = validate_and_clean_tool_name(original_name)
        
        if was_cleaned:
            app_logger.info(
                f"清理工具名称: {original_name} -> {cleaned_name}"
            )
            # 修改工具的名称
            tool.name = cleaned_name
        
        sanitized_tools.append(tool)
    
    return sanitized_tools


__all__ = [
    "is_valid_function_name",
    "clean_function_name",
    "validate_and_clean_tool_name",
    "sanitize_tool_names",
]

