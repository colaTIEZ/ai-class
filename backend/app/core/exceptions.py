"""全局异常处理 - 统一 API 错误响应格式"""

from fastapi import Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """应用自定义异常基类"""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """统一异常处理器，返回标准 API 信封格式"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "data": None,
            "message": exc.message,
            "trace_id": "",
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """兜底异常处理器"""
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "data": None,
            "message": "Internal server error",
            "trace_id": "",
        },
    )
