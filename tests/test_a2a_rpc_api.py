"""A2A JSON-RPC HTTP API 测试

覆盖场景：
- message/send 正常调用并返回 Message 结果
- 未知 method 返回 JSON-RPC 标准错误 -32601
- 无效 jsonrpc 版本返回 -32600
- params 不合法返回 -32602
- tasks/get 与 tasks/cancel 的错误返回
"""

import json
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

    response = client.post("/api/v1/a2a", json=payload)
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

    response = client.post("/api/v1/a2a", json=payload)
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

    response = client.post("/api/v1/a2a", json=payload)
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

    response = client.post("/api/v1/a2a", json=payload)
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

    response = client.post("/api/v1/a2a", json=payload)
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

    response = client.post("/api/v1/a2a", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["error"]["code"] == -32002




@patch("src.api.a2a_rpc_routes.stream_graph")
def test_message_stream_basic(mock_stream_graph):
    """message/stream 基本流式行为，返回 text/event-stream 且至少有一条 JSON-RPC data。"""

    async def fake_stream(model_name, messages, session_id):
        # 模拟两段 token 输出
        for token in ["你", "好"]:
            yield token

    mock_stream_graph.side_effect = fake_stream

    payload = {
        "jsonrpc": "2.0",
        "id": "stream-1",
        "method": "message/stream",
        "params": {
            "message": {
                "role": "user",
                "parts": [
                    {"kind": "text", "text": "流式问答测试"},
                ],
            },
            "metadata": {"foo": "bar"},
        },
    }

    response = client.post("/api/v1/a2a", json=payload)
    assert response.status_code == 200
    # 有些框架会在 content-type 后追加编码信息，这里使用 startswith 兼容
    assert response.headers["content-type"].startswith("text/event-stream")

    events = []
    for line in response.iter_lines():
        if not line:
            continue
        # TestClient.iter_lines() 已返回 str，这里直接使用即可
        line = line
        if not line.startswith("data: "):
            continue
        data = line[6:]
        if data == "[DONE]":
            break
        events.append(json.loads(data))

    # 至少收到一条事件
    assert len(events) >= 1

    first = events[0]
    assert first["jsonrpc"] == "2.0"
    assert first["id"] == "stream-1"
    assert "result" in first
    result = first["result"]
    assert "task" in result and "events" in result
    assert result["task"]["state"] in ("working", "completed")


def test_message_stream_invalid_params():
    """message/stream 在 params 缺失时以 SSE error 返回。"""

    payload = {
        "jsonrpc": "2.0",
        "id": "stream-err",
        "method": "message/stream",
        "params": {},
    }

    response = client.post("/api/v1/a2a", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    # 读取首条事件，应为 error
    for line in response.iter_lines():
        if not line:
            continue
        # TestClient.iter_lines() 已经返回 str，这里直接使用
        line = line
        if not line.startswith("data: "):
            continue
        data = line[6:]
        if data == "[DONE]":
            continue
        event = json.loads(data)
        assert "error" in event
        assert event["error"]["code"] == -32602
        break
