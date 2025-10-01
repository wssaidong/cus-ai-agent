"""
FastAPI主应用
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.config import settings
from src.utils import app_logger
from .routes import router


# 创建FastAPI应用
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="基于LangGraph的智能体API服务",
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

# 注册路由
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    """启动事件"""
    app_logger.info("=" * 50)
    app_logger.info(f"启动 {settings.api_title} v{settings.api_version}")
    app_logger.info(f"API地址: http://{settings.api_host}:{settings.api_port}")
    app_logger.info(f"文档地址: http://{settings.api_host}:{settings.api_port}/docs")
    app_logger.info(f"模型: {settings.model_name}")
    app_logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """关闭事件"""
    app_logger.info("关闭应用")


@app.get("/", tags=["根路径"])
async def root():
    """根路径"""
    return {
        "message": "欢迎使用智能体API服务",
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/api/v1/health",
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

