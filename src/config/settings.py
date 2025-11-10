"""
配置管理模块
"""
from typing import List, Optional
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """应用配置"""

    model_config = ConfigDict(
        protected_namespaces=('settings_',),
        extra='ignore',
        env_file=str(ENV_FILE),  # 使用绝对路径,确保无论在哪个目录运行都能找到 .env 文件
        env_file_encoding='utf-8',
        case_sensitive=False
    )

    # API配置
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_title: str = Field(default="智能体API服务", alias="API_TITLE")
    api_version: str = Field(default="1.0.0", alias="API_VERSION")

    # 大模型配置
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_api_base: str = Field(default="https://api.openai.com/v1", alias="OPENAI_API_BASE")
    model_name: str = Field(default="gpt-4-turbo-preview", alias="MODEL_NAME")
    temperature: float = Field(default=0.7, alias="TEMPERATURE")
    max_tokens: int = Field(default=2000, alias="MAX_TOKENS")

    # 通义千问配置
    dashscope_api_key: Optional[str] = Field(default=None, alias="DASHSCOPE_API_KEY")


    # 日志配置
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")

    # 工具配置
    enable_api_tool: bool = Field(default=True, alias="ENABLE_API_TOOL")

    # MCP工具配置
    enable_mcp_tools: bool = Field(default=False, alias="ENABLE_MCP_TOOLS")
    mcp_server_url: Optional[str] = Field(default=None, alias="MCP_SERVER_URL")
    mcp_timeout: int = Field(default=30, alias="MCP_TIMEOUT")

    # 安全配置
    cors_origins: List[str] = Field(default=["*"], alias="CORS_ORIGINS")
    api_key_enabled: bool = Field(default=False, alias="API_KEY_ENABLED")
    api_key: Optional[str] = Field(default=None, alias="API_KEY")

    # 性能配置
    max_iterations: int = Field(default=10, alias="MAX_ITERATIONS")
    timeout_seconds: int = Field(default=60, alias="TIMEOUT_SECONDS")

    # RAG知识库配置
    enable_rag_tool: bool = Field(default=False, alias="ENABLE_RAG_TOOL")
    rag_vector_db_type: str = Field(default="milvus", alias="RAG_VECTOR_DB_TYPE")
    rag_milvus_host: str = Field(default="localhost", alias="RAG_MILVUS_HOST")
    rag_milvus_port: int = Field(default=19530, alias="RAG_MILVUS_PORT")
    rag_milvus_collection: str = Field(default="knowledge_base", alias="RAG_MILVUS_COLLECTION")
    rag_milvus_user: str = Field(default="root", alias="RAG_MILVUS_USER")
    rag_milvus_password: str = Field(default="Milvus", alias="RAG_MILVUS_PASSWORD")

    # RAG Embedding 独立配置（可选，如果不设置则使用全局 OPENAI_API_KEY）
    rag_openai_api_key: Optional[str] = Field(default=None, alias="RAG_OPENAI_API_KEY")
    rag_openai_api_base: Optional[str] = Field(default=None, alias="RAG_OPENAI_API_BASE")
    rag_embedding_model: str = Field(default="text-embedding-3-small", alias="RAG_EMBEDDING_MODEL")

    # RAG 其他配置
    rag_chunk_size: int = Field(default=1000, alias="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=200, alias="RAG_CHUNK_OVERLAP")
    rag_top_k: int = Field(default=5, alias="RAG_TOP_K")

    # RAG 搜索优化配置
    rag_enable_query_optimization: bool = Field(default=True, alias="RAG_ENABLE_QUERY_OPTIMIZATION")
    rag_enable_rerank: bool = Field(default=True, alias="RAG_ENABLE_RERANK")
    rag_enable_quality_eval: bool = Field(default=True, alias="RAG_ENABLE_QUALITY_EVAL")

    # LangSmith 配置（可观测性和调试）
    langchain_tracing_v2: bool = Field(default=False, alias="LANGCHAIN_TRACING_V2")
    langchain_endpoint: str = Field(default="https://api.smith.langchain.com", alias="LANGCHAIN_ENDPOINT")
    langchain_api_key: Optional[str] = Field(default=None, alias="LANGCHAIN_API_KEY")
    langchain_project: str = Field(default="cus-ai-agent", alias="LANGCHAIN_PROJECT")

    # A2A AgentCard 配置
    a2a_enabled: bool = Field(default=False, alias="A2A_ENABLED")
    a2a_server_addresses: str = Field(default="127.0.0.1:8848", alias="A2A_SERVER_ADDRESSES")
    a2a_namespace: str = Field(default="public", alias="A2A_NAMESPACE")
    a2a_service_name: str = Field(default="cus-ai-agent", alias="A2A_SERVICE_NAME")
    a2a_username: Optional[str] = Field(default=None, alias="A2A_USERNAME")
    a2a_password: Optional[str] = Field(default=None, alias="A2A_PASSWORD")

    # A2A 服务 URL 配置（用于 AgentCard 注册）
    a2a_service_host: Optional[str] = Field(default=None, alias="A2A_SERVICE_HOST")
    a2a_service_port: Optional[int] = Field(default=None, alias="A2A_SERVICE_PORT")
    a2a_service_url: Optional[str] = Field(default=None, alias="A2A_SERVICE_URL")


# 全局配置实例
settings = Settings()

