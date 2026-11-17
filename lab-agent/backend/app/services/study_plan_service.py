from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.study_plan import StudyPlan
from app.models.user import User
from app.schemas.study_plan import StudyPlanCreateRequest, StudyPlanResponse

STUDY_PLAN_MAX_LENGTH = 2000
# 给 AI 参考时最多带多少条历史计划，避免 prompt 无限膨胀
STUDY_PLAN_RECENT_LIMIT = 20


def list_page_plans(
    db: Session, current_user: User, page: int = 1, page_size: int = 10
) -> PageResponse:
    """查询学习计划分页列表"""

    query = db.query(StudyPlan).filter(StudyPlan.user_id == current_user.id)
    total = query.count()
    rows = (
        query.order_by(StudyPlan.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PageResponse(
        list=[StudyPlanResponse.model_validate(row) for row in rows],
        total=total,
    )


def create_study_plan(
    db: Session, current_user: User, data: StudyPlanCreateRequest
) -> StudyPlanResponse:
    """创建学习计划"""
    if not data.content:
        raise BusinessException("学习计划内容不能为空")
    if len(data.content) > STUDY_PLAN_MAX_LENGTH:
        raise BusinessException(f"学习计划内容不能超过{STUDY_PLAN_MAX_LENGTH}")
    row = StudyPlan(user_id=current_user.id, content=data.content)
    db.add(row)
    db.commit()
    db.refresh(row)
    return StudyPlanResponse.model_validate(row)


def delete_study_plan(db: Session, current_user: User, plan_id: int) -> None:
    """删除学习计划"""
    row = (
        db.query(StudyPlan)
        .filter(StudyPlan.id == plan_id, StudyPlan.user_id == current_user.id)
        .first()
    )
    if not row:
        raise BusinessException("学习计划不存在")
    db.delete(row)
    db.commit()


def list_recent_plans(
    db: Session, current_user: User, limit: int = STUDY_PLAN_RECENT_LIMIT
) -> list[dict]:
    """取当前用户最近的学习计划，给 AI 工具用（不分页，避免把整表塞进 prompt）"""
    rows = (
        db.query(StudyPlan)
        .filter(StudyPlan.user_id == current_user.id)
        .order_by(StudyPlan.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": row.id,
            "content": row.content,
            "create_time": row.create_time.strftime("%Y-%m-%d %H:%M")
            if row.create_time
            else None,
        }
        for row in rows
    ]
