from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.response import Response
from app.database import get_db
from app.dependence.auth import get_current_user
from app.models.user import User
from app.schemas.user import UserUpdateRequest
from app.services import user_service

router = APIRouter(prefix="/user", tags=["用户信息"])


@router.get("/info")
def get_user_info(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return Response.success(data=user_service.get_user_info(current_user))


@router.put("/update")
def update_user_info(
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    res = user_service.update_user_info(db, current_user, data)
    return Response.success(data=res)
