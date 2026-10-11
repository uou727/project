from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.common.response import Response


class BusinessException(Exception):
    """自定义的业务异常类"""

    def __init__(self, message: str, code: int = 400):
        self.code = code
        self.message = message
        super().__init__(message)


async def business_exception_handler(request: Request, exc: BusinessException):
    """自定义的业务异常处理函数"""
    return JSONResponse(
        status_code=200,
        content=Response.error(code=exc.code, message=exc.message).model_dump(),
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """自定义的HTTP异常处理函数"""
    return JSONResponse(
        status_code=200,
        content=Response.error(code=exc.status_code, message=exc.detail).model_dump(),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """自定义的验证异常处理函数"""
    return JSONResponse(
        status_code=422,
        content=Response.error(code=422, message="请求参数校验错误").model_dump(),
    )


async def global_excpetion_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    return JSONResponse(
        status_code=500,
        content=Response.error(code=500, message="服务器内部错误").model_dump(),
    )
