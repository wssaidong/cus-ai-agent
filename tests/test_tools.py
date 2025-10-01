"""
工具测试
"""
import pytest
from src.tools.custom_tools import CalculatorTool, TextProcessTool


def test_calculator_tool():
    """测试计算器工具"""
    tool = CalculatorTool()
    
    # 测试加法
    result = tool._run("10 + 20")
    assert result == "30"
    
    # 测试乘法
    result = tool._run("5 * 6")
    assert result == "30"
    
    # 测试复杂表达式
    result = tool._run("(10 + 20) * 2")
    assert result == "60"


def test_text_process_tool():
    """测试文本处理工具"""
    tool = TextProcessTool()
    
    # 测试大写转换
    result = tool._run("uppercase|hello world")
    assert result == "HELLO WORLD"
    
    # 测试小写转换
    result = tool._run("lowercase|HELLO WORLD")
    assert result == "hello world"
    
    # 测试反转
    result = tool._run("reverse|hello")
    assert result == "olleh"
    
    # 测试长度
    result = tool._run("length|hello")
    assert result == "5"


def test_calculator_invalid_input():
    """测试计算器工具的无效输入"""
    tool = CalculatorTool()
    
    # 测试非法字符
    result = tool._run("import os")
    assert "错误" in result or "失败" in result


def test_text_process_invalid_format():
    """测试文本处理工具的无效格式"""
    tool = TextProcessTool()
    
    # 测试无效格式
    result = tool._run("invalid_input")
    assert "错误" in result

