"""A2A JSON-RPC HTTP API 测试

覆盖场景：
- message/send 正常调用并返回 Message 结果
- 未知 method 返回 JSON-RPC 标准错误 -32601
- 无效 jsonrpc 版本返回 -32600
- params 不合法返回 -32602
- tasks/get 与 tasks/cancel 的错误返回
"""

from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from src.api.main import app


client = TestClient(app)


@patch("src.api.a2a_rpc_routes.get_chat_graph")
def test_message_send_success(mock_get_graph):
    """message/send 正常路径，返回 kind=message 的结果。"""
    mock_graph = Mock()
    mock_graph.ainvoke = AsyncMock(return_value={"messages": [AIMessage(content="你好，我是 A2A 测试智能体")]})
    mock_get_graph.return_value = mock_graph

    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [
                    {"kind": "text", "text": "你好，请简单自我介绍一下"}
                ],
            },
            "metadata": {},
        },
    }

    response = client.post("/a2a/v1", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == "1"
    assert "result" in data and "error" not in data

    result = data["result"]
    assert result["kind"] == "message"
    assert result["parts"][0]["kind"] == "text"
    assert "A2A 测试智能体" in result["parts"][0]["text"]


def test_method_not_found():
    """未知 method 返回 -32601。"""
    payload = {
        "jsonrpc": "2.0",
        "id": "2",
        "method": "unknown/method",
        "params": {},
    }

    response = client.post("/a2a/v1", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["error"]["code"] == -32601


def test_invalid_jsonrpc_version():
    """jsonrpc 版本非 2.0 时返回 -32600。"""
    payload = {
        "jsonrpc": "1.0",
        "id": "3",
        "method": "message/send",
        "params": {},
    }

    response = client.post("/a2a/v1", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["error"]["code"] == -32600


def test_invalid_params_no_message():
    """缺少 message 字段时返回 -32602。"""
    payload = {
        "jsonrpc": "2.0",
        "id": "4",
        "method": "message/send",
        "params": {},
    }

    response = client.post("/a2a/v1", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["error"]["code"] == -32602


def test_tasks_get_not_found():
    """tasks/get 始终视为 TaskNotFound。"""
    payload = {
        "jsonrpc": "2.0",
        "id": "5",
        "method": "tasks/get",
        "params": {"id": "non-existent"},
    }

    response = client.post("/a2a/v1", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["error"]["code"] == -32001


def test_tasks_cancel_not_supported():
    """tasks/cancel 返回不可取消错误。"""
    payload = {
        "jsonrpc": "2.0",
        "id": "6",
        "method": "tasks/cancel",
        "params": {"id": "non-existent"},
    }

    response = client.post("/a2a/v1", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["error"]["code"] == -32002

