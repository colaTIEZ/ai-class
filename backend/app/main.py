"""FastAPI 应用入口 - ai-class 后端服务"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    generic_exception_handler,
)
from app.api.v1.health import router as health_router

from contextlib import asynccontextmanager
from app.services.processing_queue import processing_queue

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if not settings.embedding_ready:
        logger.critical(
            "OPENAI_API_KEY is missing; embedding-related processing is unavailable."
        )
    processing_queue.start_worker()
    yield
    # Shutdown
    await processing_queue.stop_worker()

def create_app() -> FastAPI:
    """工厂函数创建 FastAPI 实例"""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # CORS 中间件配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册全局异常处理器
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # 注册路由
    from app.api.v1.health import router as health_router
    from app.api.v1.documents import router as documents_router
    
    app.include_router(health_router, prefix="/api/v1", tags=["health"])
    app.include_router(documents_router, prefix="/api/v1/documents", tags=["documents"])

    return app


app = create_app()
