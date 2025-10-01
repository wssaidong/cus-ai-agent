"""
API接口测试
"""
import pytest
from fastapi.testclient import TestClient
from src.api.main import app


client = TestClient(app)


def test_root():
    """测试根路径"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_health():
    """测试健康检查"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


def test_chat_basic():
    """测试基本对话"""
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "你好",
            "session_id": "test-session"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "session_id" in data
    assert "metadata" in data


def test_chat_calculator():
    """测试计算器工具"""
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "帮我计算 10 + 20",
            "session_id": "test-calc"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    # 响应中应该包含计算结果
    assert "30" in data["response"]


def test_chat_text_process():
    """测试文本处理工具"""
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "请把 hello 转换为大写",
            "session_id": "test-text"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data


def test_chat_invalid_request():
    """测试无效请求"""
    response = client.post(
        "/api/v1/chat",
        json={
            "session_id": "test-invalid"
            # 缺少message字段
        }
    )
    assert response.status_code == 422  # Validation error


def test_openapi_schema():
    """测试OpenAPI规范"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert "paths" in data

