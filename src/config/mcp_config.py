"""
MCP 工具配置管理模块
"""
import yaml
from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field
from src.utils import app_logger


class MCPServerConfig(BaseModel):
    """单个 MCP 服务器配置"""
    name: str = Field(..., description="服务器名称")
    enabled: bool = Field(default=False, description="是否启用")
    url: str = Field(..., description="服务器地址")
    timeout: Optional[int] = Field(default=None, description="超时时间（秒）")
    description: Optional[str] = Field(default="", description="描述信息")
    tags: List[str] = Field(default_factory=list, description="标签")
    tool_prefix: Optional[str] = Field(default=None, description="工具名称前缀")


class MCPGlobalConfig(BaseModel):
    """MCP 全局配置"""
    enabled: bool = Field(default=False, description="全局启用/禁用")
    default_timeout: int = Field(default=30, description="默认超时时间")
    connect_timeout: int = Field(default=3, description="连接超时时间")
    startup_max_timeout: int = Field(default=5, description="启动时最大等待时间")


class MCPToolsConfig(BaseModel):
    """MCP 工具配置"""
    global_config: MCPGlobalConfig = Field(default_factory=MCPGlobalConfig, alias="global")
    servers: List[MCPServerConfig] = Field(default_factory=list, description="服务器列表")

    class Config:
        populate_by_name = True


class MCPConfigManager:
    """MCP 配置管理器"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为项目根目录下的 config/mcp_tools.yaml
        """
        if config_path is None:
            # 默认配置文件路径
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "mcp_tools.yaml"
        
        self.config_path = config_path
        self._config: Optional[MCPToolsConfig] = None
    
    def load_config(self) -> MCPToolsConfig:
        """
        加载配置文件
        
        Returns:
            MCP 工具配置
        """
        if self._config is not None:
            return self._config
        
        try:
            if not self.config_path.exists():
                app_logger.warning(f"MCP 配置文件不存在: {self.config_path}，使用默认配置")
                self._config = MCPToolsConfig()
                return self._config
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                app_logger.warning("MCP 配置文件为空，使用默认配置")
                self._config = MCPToolsConfig()
                return self._config
            
            self._config = MCPToolsConfig(**config_data)
            app_logger.info(f"成功加载 MCP 配置文件: {self.config_path}")
            return self._config
            
        except Exception as e:
            app_logger.error(f"加载 MCP 配置文件失败: {str(e)}")
            self._config = MCPToolsConfig()
            return self._config
    
    def get_enabled_servers(self) -> List[MCPServerConfig]:
        """
        获取所有启用的服务器配置
        
        Returns:
            启用的服务器配置列表
        """
        config = self.load_config()
        
        # 如果全局禁用，返回空列表
        if not config.global_config.enabled:
            app_logger.info("MCP 工具全局禁用")
            return []
        
        # 筛选启用的服务器
        enabled_servers = [server for server in config.servers if server.enabled]
        
        if enabled_servers:
            app_logger.info(f"找到 {len(enabled_servers)} 个启用的 MCP 服务器: {[s.name for s in enabled_servers]}")
        else:
            app_logger.info("没有启用的 MCP 服务器")
        
        return enabled_servers
    
    def get_server_by_name(self, name: str) -> Optional[MCPServerConfig]:
        """
        根据名称获取服务器配置
        
        Args:
            name: 服务器名称
            
        Returns:
            服务器配置，如果不存在则返回 None
        """
        config = self.load_config()
        for server in config.servers:
            if server.name == name:
                return server
        return None
    
    def get_server_timeout(self, server: MCPServerConfig) -> int:
        """
        获取服务器的超时时间
        
        Args:
            server: 服务器配置
            
        Returns:
            超时时间（秒）
        """
        config = self.load_config()
        return server.timeout if server.timeout is not None else config.global_config.default_timeout
    
    def get_global_config(self) -> MCPGlobalConfig:
        """
        获取全局配置
        
        Returns:
            全局配置
        """
        config = self.load_config()
        return config.global_config
    
    def reload_config(self):
        """重新加载配置文件"""
        self._config = None
        return self.load_config()
    
    def is_enabled(self) -> bool:
        """
        检查 MCP 工具是否启用
        
        Returns:
            是否启用
        """
        config = self.load_config()
        return config.global_config.enabled and len(self.get_enabled_servers()) > 0


# 全局配置管理器实例
mcp_config_manager = MCPConfigManager()

