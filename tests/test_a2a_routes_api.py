"""
A2A HTTP API 协议兼容性测试

基于 docs/A2A_STANDALONE_QUICK_REFERENCE.md 和 src/api/a2a_routes.py，
验证 /api/v1/a2a 下各端点的请求/响应结构是否符合约定。
"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


@pytest.fixture
def mock_a2a_manager():
    """构造一个符合协议的 AgentCardManager mock。"""
    manager = Mock()

    # create_agent_card 返回 True 表示创建成功
    manager.create_agent_card.return_value = True

    # get_agent_card 返回一个典型的 AgentCard 结构
    manager.get_agent_card.return_value = {
        "name": "my-agent",
        "description": "我的智能体",
        "version": "1.0.0",
        "url": "http://127.0.0.1:8000/a2a/v1",
        "protocol_version": "0.2.9",
        "preferred_transport": "JSONRPC",
        "registration_type": "SERVICE",
        "skills": [
            {
                "id": "chat",
                "name": "对话",
                "description": "智能对话功能",
                "tags": ["chat", "conversation"],
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
            }
        ],
    }

    # list_agent_cards 返回分页列表结构（示例）
    manager.list_agent_cards.return_value = {
        "pageNo": 1,
        "pageSize": 100,
        "count": 1,
        "agentCards": [manager.get_agent_card.return_value],
    }

    # get_version_list 返回版本列表
    manager.get_version_list.return_value = ["1.0.0", "1.0.1"]

    # delete_agent_card 返回 True 表示删除成功
    manager.delete_agent_card.return_value = True

    return manager


@patch("src.api.a2a_routes.get_agent_card_manager")
def test_create_agent_card_protocol(mock_get_manager, mock_a2a_manager):
    """POST /api/v1/a2a/agent-cards 创建 AgentCard 协议检查。"""
    mock_get_manager.return_value = mock_a2a_manager

    payload = {
        "name": "my-agent",
        "description": "我的智能体",
        "version": "1.0.0",
        "url": "http://127.0.0.1:8000/a2a/v1",
        "protocol_version": "0.2.9",
        "preferred_transport": "JSONRPC",
        "registration_type": "SERVICE",
        "skills": [
            {
                "id": "chat",
                "name": "对话",
                "description": "智能对话功能",
                "tags": ["chat", "conversation"],
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
            }
        ],
    }

    response = client.post("/api/v1/a2a/agent-cards", json=payload)
    assert response.status_code == 200

    data = response.json()
    # 协议封装：code/message/data
    assert data["code"] == 0
    assert data["message"] == "success"
    assert "data" in data
    assert data["data"]["name"] == payload["name"]
    assert data["data"]["version"] == payload["version"]

    # 确认内部管理器调用参数符合 AgentCard 协议字段
    mock_a2a_manager.create_agent_card.assert_called_once()
    _, call_kwargs = mock_a2a_manager.create_agent_card.call_args
    assert call_kwargs["name"] == payload["name"]
    assert call_kwargs["description"] == payload["description"]
    assert call_kwargs["version"] == payload["version"]
    assert call_kwargs["url"] == payload["url"]
    assert call_kwargs["protocol_version"] == payload["protocol_version"]
    assert call_kwargs["preferred_transport"] == payload["preferred_transport"]
    assert call_kwargs["registration_type"] == payload["registration_type"]
    assert call_kwargs["skills"] == payload["skills"]


@patch("src.api.a2a_routes.get_agent_card_manager")
def test_get_agent_card_protocol(mock_get_manager, mock_a2a_manager):
    """GET /api/v1/a2a/agent-cards/{agent_name} 协议检查。"""
    mock_get_manager.return_value = mock_a2a_manager

    response = client.get(
        "/api/v1/a2a/agent-cards/my-agent",
        params={"version": "1.0.0", "registration_type": "SERVICE"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["code"] == 0
    assert data["message"] == "success"
    assert isinstance(data["data"], dict)
    assert data["data"]["name"] == "my-agent"
    assert data["data"]["version"] == "1.0.0"
    assert data["data"]["protocol_version"] == "0.2.9"
    assert data["data"]["preferred_transport"] == "JSONRPC"


@patch("src.api.a2a_routes.get_agent_card_manager")
def test_list_agent_cards_protocol(mock_get_manager, mock_a2a_manager):
    """GET /api/v1/a2a/agent-cards 列表协议检查。"""
    mock_get_manager.return_value = mock_a2a_manager

    response = client.get("/api/v1/a2a/agent-cards", params={"page_no": 1, "page_size": 10})
    assert response.status_code == 200

    data = response.json()
    assert data["code"] == 0
    assert data["message"] == "success"
    assert isinstance(data["data"], dict)
    # 只检查存在列表相关字段，不强约束字段名（兼容 agentCards / agent_cards）
    assert (
        "agentCards" in data["data"]
        or "agent_cards" in data["data"]
        or "items" in data["data"]
    )


@patch("src.api.a2a_routes.get_agent_card_manager")
def test_delete_agent_card_protocol(mock_get_manager, mock_a2a_manager):
    """DELETE /api/v1/a2a/agent-cards/{agent_name} 协议检查。"""
    mock_get_manager.return_value = mock_a2a_manager

    response = client.delete(
        "/api/v1/a2a/agent-cards/my-agent",
        params={"version": "1.0.0"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["code"] == 0
    assert data["message"] == "success"
    assert data["data"]["name"] == "my-agent"


@patch("src.api.a2a_routes.get_agent_card_manager")
def test_get_agent_card_versions_protocol(mock_get_manager, mock_a2a_manager):
    """GET /api/v1/a2a/agent-cards/{agent_name}/versions 协议检查。"""
    mock_get_manager.return_value = mock_a2a_manager

    response = client.get("/api/v1/a2a/agent-cards/my-agent/versions")
    assert response.status_code == 200

    data = response.json()
    assert data["code"] == 0
    assert data["message"] == "success"
    assert "versions" in data["data"]
    assert isinstance(data["data"]["versions"], list)

