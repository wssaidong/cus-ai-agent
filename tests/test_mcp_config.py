"""
MCP 配置和工具过滤测试
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from src.config.mcp_config import (
    MCPServerConfig,
    MCPToolsFilter,
    MCPGlobalConfig,
    MCPToolsConfig,
    MCPConfigManager,
)


class TestMCPToolsFilter:
    """MCP 工具过滤配置测试"""

    def test_tools_filter_with_include(self):
        """测试包含白名单的工具过滤"""
        filter_config = MCPToolsFilter(
            include=["search", "get_index_info"]
        )
        assert filter_config.include == ["search", "get_index_info"]
        assert filter_config.exclude is None

    def test_tools_filter_with_exclude(self):
        """测试包含黑名单的工具过滤"""
        filter_config = MCPToolsFilter(
            exclude=["delete_index", "drop_table"]
        )
        assert filter_config.exclude == ["delete_index", "drop_table"]
        assert filter_config.include is None

    def test_tools_filter_empty(self):
        """测试空的工具过滤"""
        filter_config = MCPToolsFilter()
        assert filter_config.include is None
        assert filter_config.exclude is None


class TestMCPServerConfig:
    """MCP 服务器配置测试"""

    def test_server_config_with_tools_filter(self):
        """测试包含工具过滤的服务器配置"""
        tools_filter = MCPToolsFilter(include=["search", "get_info"])
        server = MCPServerConfig(
            name="elasticsearch-mcp",
            enabled=True,
            url="http://localhost:9200",
            description="Elasticsearch MCP",
            tools=tools_filter,
        )
        assert server.name == "elasticsearch-mcp"
        assert server.enabled is True
        assert server.tools is not None
        assert server.tools.include == ["search", "get_info"]

    def test_server_config_without_tools_filter(self):
        """测试不包含工具过滤的服务器配置"""
        server = MCPServerConfig(
            name="test-mcp",
            enabled=True,
            url="http://localhost:3000",
        )
        assert server.tools is None


class TestMCPConfigManager:
    """MCP 配置管理器测试"""

    @pytest.fixture
    def config_manager(self):
        """创建配置管理器实例"""
        # 使用临时配置文件
        config_path = Path(__file__).parent / "test_mcp_config.yaml"
        return MCPConfigManager(config_path)

    def test_should_include_tool_no_filter(self, config_manager):
        """测试没有过滤配置时，所有工具都应该被包含"""
        # 创建没有工具过滤的服务器配置
        server = MCPServerConfig(
            name="test-server",
            enabled=True,
            url="http://localhost:3000",
        )
        config_manager._config = MCPToolsConfig(servers=[server])

        # 所有工具都应该被包含
        assert config_manager.should_include_tool("test-server", "any_tool") is True
        assert config_manager.should_include_tool("test-server", "another_tool") is True

    def test_should_include_tool_with_include_filter(self, config_manager):
        """测试使用白名单过滤工具"""
        tools_filter = MCPToolsFilter(include=["search", "get_info"])
        server = MCPServerConfig(
            name="elasticsearch-mcp",
            enabled=True,
            url="http://localhost:9200",
            tools=tools_filter,
        )
        config_manager._config = MCPToolsConfig(servers=[server])

        # 白名单中的工具应该被包含
        assert config_manager.should_include_tool("elasticsearch-mcp", "search") is True
        assert config_manager.should_include_tool("elasticsearch-mcp", "get_info") is True

        # 不在白名单中的工具应该被排除
        assert config_manager.should_include_tool("elasticsearch-mcp", "delete_index") is False
        assert config_manager.should_include_tool("elasticsearch-mcp", "other_tool") is False

    def test_should_include_tool_with_exclude_filter(self, config_manager):
        """测试使用黑名单过滤工具"""
        tools_filter = MCPToolsFilter(exclude=["delete_index", "drop_table"])
        server = MCPServerConfig(
            name="database-mcp",
            enabled=True,
            url="http://localhost:5432",
            tools=tools_filter,
        )
        config_manager._config = MCPToolsConfig(servers=[server])

        # 不在黑名单中的工具应该被包含
        assert config_manager.should_include_tool("database-mcp", "query") is True
        assert config_manager.should_include_tool("database-mcp", "insert") is True

        # 在黑名单中的工具应该被排除
        assert config_manager.should_include_tool("database-mcp", "delete_index") is False
        assert config_manager.should_include_tool("database-mcp", "drop_table") is False

    def test_should_include_tool_nonexistent_server(self, config_manager):
        """测试不存在的服务器"""
        config_manager._config = MCPToolsConfig(servers=[])

        # 不存在的服务器的工具应该被包含（默认行为）
        assert config_manager.should_include_tool("nonexistent-server", "any_tool") is True

    def test_include_takes_precedence_over_exclude(self, config_manager):
        """测试 include 优先级高于 exclude"""
        # 虽然配置中同时有 include 和 exclude，但 include 应该优先
        tools_filter = MCPToolsFilter(
            include=["search", "get_info"],
            exclude=["search"],  # 这个应该被忽略
        )
        server = MCPServerConfig(
            name="test-mcp",
            enabled=True,
            url="http://localhost:3000",
            tools=tools_filter,
        )
        config_manager._config = MCPToolsConfig(servers=[server])

        # include 中的工具应该被包含
        assert config_manager.should_include_tool("test-mcp", "search") is True
        assert config_manager.should_include_tool("test-mcp", "get_info") is True

        # 不在 include 中的工具应该被排除
        assert config_manager.should_include_tool("test-mcp", "delete") is False


class TestMCPToolsFilterIntegration:
    """MCP 工具过滤集成测试"""

    def test_config_loading_with_tools_filter(self):
        """测试加载包含工具过滤的配置"""
        config_data = {
            "global": {
                "enabled": True,
                "default_timeout": 30,
            },
            "servers": [
                {
                    "name": "elasticsearch-mcp",
                    "enabled": True,
                    "url": "http://localhost:9200",
                    "tools": {
                        "include": ["search", "get_index_info"],
                    },
                },
                {
                    "name": "database-mcp",
                    "enabled": True,
                    "url": "http://localhost:5432",
                    "tools": {
                        "exclude": ["delete_index", "drop_table"],
                    },
                },
            ],
        }

        config = MCPToolsConfig(**config_data)

        # 验证第一个服务器的配置
        assert config.servers[0].name == "elasticsearch-mcp"
        assert config.servers[0].tools is not None
        assert config.servers[0].tools.include == ["search", "get_index_info"]

        # 验证第二个服务器的配置
        assert config.servers[1].name == "database-mcp"
        assert config.servers[1].tools is not None
        assert config.servers[1].tools.exclude == ["delete_index", "drop_table"]

