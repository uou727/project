from fastapi import APIRouter, Depends

from app.dependence.auth import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/user", tags=["用户信息"])


@router.get("/info")
def get_user_info(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return {
        "code": 200,
        "message": "获取用户信息成功",
        "data": UserResponse.model_validate(current_user),
    }
