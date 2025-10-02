"""
自定义工具
"""
from typing import Optional
from langchain.tools import BaseTool
from pydantic import Field
from src.utils import app_logger


class CalculatorTool(BaseTool):
    """计算器工具"""
    
    name: str = "calculator"
    description: str = """
    执行数学计算。
    输入应该是一个数学表达式，例如：2 + 2 或 10 * 5
    返回计算结果。
    """
    
    def _run(self, expression: str) -> str:
        """执行计算"""
        try:
            # 安全地执行数学表达式
            # 只允许数字、运算符和括号
            allowed_chars = set("0123456789+-*/().% ")
            if not all(c in allowed_chars for c in expression):
                return "错误：表达式包含非法字符"
            
            result = eval(expression)
            return str(result)
            
        except Exception as e:
            app_logger.error(f"计算失败: {str(e)}")
            return f"计算失败: {str(e)}"
    
    async def _arun(self, expression: str) -> str:
        """异步执行计算"""
        return self._run(expression)


class TextProcessTool(BaseTool):
    """文本处理工具"""
    
    name: str = "text_process"
    description: str = """
    处理文本，支持以下操作：
    - uppercase: 转换为大写
    - lowercase: 转换为小写
    - reverse: 反转文本
    - length: 获取文本长度
    
    输入格式：操作类型|文本内容
    例如：uppercase|hello world
    """
    
    def _run(self, query: str) -> str:
        """执行文本处理"""
        try:
            parts = query.split("|", 1)
            if len(parts) != 2:
                return "错误：输入格式应为 操作类型|文本内容"
            
            operation, text = parts
            operation = operation.strip().lower()

            if operation == "uppercase":
                return text.upper()
            elif operation == "lowercase":
                return text.lower()
            elif operation == "reverse":
                return text[::-1]
            elif operation == "length":
                return str(len(text))
            else:
                return f"错误：不支持的操作类型 {operation}"
                
        except Exception as e:
            app_logger.error(f"文本处理失败: {str(e)}")
            return f"文本处理失败: {str(e)}"
    
    async def _arun(self, query: str) -> str:
        """异步执行文本处理"""
        return self._run(query)

