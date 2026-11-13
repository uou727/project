from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.response import Response
from app.database import get_db
from app.dependence.auth import get_current_user
from app.models.user import User
from app.schemas.study_plan import StudyPlanCreateRequest
from app.services import study_plan_service

router = APIRouter(prefix="/study-plans", tags=["学习计划相关的API接口"])


@router.get("")
def get_my_page_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = 1,
    page_size: int = 10,
):
    """查询我的学习计划分页列表"""
    data = study_plan_service.list_page_plans(db, current_user, page, page_size)
    return Response.success(data=data)


@router.post("")
def create_my_study_plan(
    data: StudyPlanCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建我的学习计划"""
    study_plan = study_plan_service.create_study_plan(db, current_user, data)
    return Response.success(data=study_plan)


@router.delete("/{plan_id}")
def delete_my_study_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除我的学习计划"""
    study_plan_service.delete_study_plan(db, current_user, plan_id)
    return Response.success(message="删除成功")
