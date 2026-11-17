from typing import Any

from pydantic import BaseModel


class Response(BaseModel):
    """统一封装的返回格式"""

    code: int = 200
    message: str = "success"
    data: Any = None

    @classmethod
    def success(cls, message: str = "success", data: Any = None) -> "Response":
        """成功响应：code=200，可自定义 message 和 data。"""
        return cls(code=200, message=message, data=data)

    @classmethod
    def error(cls, code: int = 400, message: str = "请求失败") -> "Response":
        """失败响应：code 默认 400，message 直接展示给前端。"""
        return cls(code=code, message=message)


class PageResponse(BaseModel):
    list: Any = []
    total: int = 0
