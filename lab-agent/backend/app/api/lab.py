from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.response import Response
from app.database import get_db
from app.dependence.auth import get_current_admin
from app.models.user import User
from app.schemas.lab import LabCreateRequest, LabUpdateRequest
from app.services import lab_service

router = APIRouter(prefix="/lab", tags=["实验室信息接口"])


@router.get("/list")
def get_lab_list(
    page: int = 1,
    page_size: int = 10,
    keywords: str | None = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员查询用户信息"""
    res = lab_service.get_lab_page_list(db, page, page_size, keywords)
    return Response.success(data=res)


@router.post("")
def create_lab(
    data: LabCreateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员创建用户信息"""
    res = lab_service.create_lab(db, data)
    return Response.success(data=res)


@router.put("/{lab_id}")
def update_lab(
    lab_id: int,
    data: LabUpdateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """更新用户信息"""
    res = lab_service.update_lab(db, lab_id, data)
    return Response.success(data=res)


@router.delete("/{lab_id}")
def delete_lab(
    lab_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """删除用户"""
    lab_service.delete_lab(db, lab_id)
    return Response.success()
