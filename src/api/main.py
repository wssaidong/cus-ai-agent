"""
FastAPI主应用
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.config import settings
from src.utils import app_logger
from src.utils.a2a_auto_register import get_a2a_auto_register
from .routes import router
from .knowledge_routes import router as knowledge_router
from .recommendation_routes import router as recommendation_router
from .a2a_routes import router as a2a_router
from .openai_routes import router as openai_router
# from .multi_agent_routes import router as multi_agent_router  # 旧架构，已废弃

# 导入 a2a-sdk 的 FastAPI 应用
from a2a.server.apps.jsonrpc.fastapi_app import A2AFastAPIApplication
from a2a.types import AgentCard, AgentCapabilities, AgentSkill
from .a2a_rpc_routes import get_a2a_request_handler


# 创建FastAPI应用
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="基于LangGraph的智能体API服务，支持RAG知识库和OpenAI兼容API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建 AgentCard
agent_card = AgentCard(
    name="cus-ai-agent",
    description="基于 LangGraph 的智能体服务，支持 RAG 知识库和多智能体协作",
    url=f"http://{settings.api_host}:{settings.api_port}/api/v1/a2a",
    version="1.0.0",
    capabilities=AgentCapabilities(
        streaming=True,
        pushNotifications=False,
        stateTransitionHistory=True,
    ),
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    skills=[
        AgentSkill(
            id="chat",
            name="智能对话",
            description="支持多轮对话、知识库检索和工具调用",
            tags=["chat", "rag", "tools"],
        ),
        AgentSkill(
            id="knowledge-search",
            name="知识库检索",
            description="从向量数据库检索相关知识",
            tags=["rag", "search"],
        ),
    ],
)

# 创建 A2A JSON-RPC 应用（使用 a2a-sdk 官方实现）
a2a_jsonrpc_app = A2AFastAPIApplication(
    agent_card=agent_card,
    http_handler=get_a2a_request_handler(),
)

# 将 A2A JSON-RPC 路由添加到主应用
a2a_jsonrpc_app.add_routes_to_app(app, rpc_url="/api/v1/a2a")
app_logger.info("A2A JSON-RPC API 已注册到 /api/v1/a2a (使用 a2a-sdk)")

# OpenAI 兼容 API（/v1 前缀）
app.include_router(openai_router)
app_logger.info("OpenAI 兼容 API 已注册到 /v1 前缀")

# 原有路由（保持向后兼容）
app.include_router(router)
app.include_router(knowledge_router)
app.include_router(recommendation_router)
app.include_router(a2a_router)
# app.include_router(multi_agent_router)  # 旧架构，已废弃


@app.on_event("startup")
async def startup_event():
    """启动事件"""
    app_logger.info("=" * 50)
    app_logger.info(f"启动 {settings.api_title} v{settings.api_version}")
    app_logger.info(f"API地址: http://{settings.api_host}:{settings.api_port}")
    app_logger.info(f"文档地址: http://{settings.api_host}:{settings.api_port}/docs")
    app_logger.info(f"模型: {settings.model_name}")

    # 异步加载 MCP 工具
    try:
        from src.tools import load_mcp_tools_async
        mcp_tools = await load_mcp_tools_async()
        if mcp_tools:
            app_logger.info(f"✓ 成功加载 {len(mcp_tools)} 个 MCP 工具")
            for tool in mcp_tools:
                app_logger.info(f"  - {tool.name}")
        else:
            app_logger.info("未加载 MCP 工具")
    except Exception as e:
        app_logger.error(f"加载 MCP 工具失败: {str(e)}")

    # 初始化并注册 A2A AgentCard
    try:
        a2a_register = get_a2a_auto_register()
        if await a2a_register.initialize():
            # 自动注册 AgentCard
            await a2a_register.register_agent_card()
        else:
            app_logger.warning("A2A 自动注册初始化失败，AgentCard 未注册")
    except Exception as e:
        app_logger.error(f"A2A AgentCard 注册失败: {str(e)}")

    app_logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """关闭事件"""
    app_logger.info("关闭应用")

    # 注销 A2A AgentCard
    try:
        a2a_register = get_a2a_auto_register()
        if a2a_register.registered:
            await a2a_register.deregister_agent_card()
        await a2a_register.close()
    except Exception as e:
        app_logger.error(f"A2A AgentCard 注销失败: {str(e)}")


@app.get("/", tags=["根路径"])
async def root():
    """根路径"""
    return {
        "message": "欢迎使用智能体API服务",
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/api/v1/health",
        "a2a_api": {
            "a2a_rpc": "/api/v1/a2a",
            "description": "A2A 协议端点 (SDK 和自定义实现)"
        },
        "openai_api": {
            "chat_completions": "/v1/chat/completions",
            "models": "/v1/models",
            "description": "OpenAI 兼容 API 端点"
        }
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    app_logger.error(f"全局异常: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc),
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )

