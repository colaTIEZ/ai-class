"""健康检查端点 - 验证前后端连通性"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """基础健康检查，返回标准 API 信封格式"""
    return {
        "status": "success",
        "data": {
            "service": "ai-class",
            "version": "0.1.0",
            "health": "ok",
        },
        "message": "",
        "trace_id": "",
    }
