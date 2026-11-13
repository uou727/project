from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.models.course import Course
from app.models.schedule import Schedule
from app.schemas.course import CourseCreateRequest, CourseResponse, CourseUpdateRequest


def list_courses(db: Session, keywords: str | None = None) -> list[CourseResponse]:
    """模糊查询课程列表"""
    query = db.query(Course)
    if keywords and keywords.strip():
        kw = f"%{keywords.strip()}%"
        query = query.filter(
            or_(
                Course.name.ilike(f"%{kw}%"),
                Course.code.ilike(f"%{kw}%"),
                Course.description.ilike(f"%{kw}%"),
            )
        )
    rows = query.order_by(Course.id.desc()).all()
    result_list = []
    for row in rows:
        resp_obj = CourseResponse.model_validate(row)
        result_list.append(resp_obj)
    return result_list


# return [CourseResponse.model_validate(row) for row in rows]


def create_course(db: Session, data: CourseCreateRequest):
    """新增"""
    if not data.name.strip():
        raise BusinessException(message="课程名称必传")
    if not data.code.strip():
        raise BusinessException(message="课程编码必传")
    exist = db.query(Course).filter(Course.name == data.name).first()
    if exist:
        raise BusinessException(message="课程已存在")
    course = Course(
        name=data.name.strip(),
        code=data.code.strip(),
        description=(data.description or "").strip() or None,
        status=data.status if data.status in (0, 1) else 1,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return CourseResponse.model_validate(course)


def update_course(
    db: Session, course_id: int, data: CourseUpdateRequest
) -> CourseResponse:
    """更新课程"""
    row = db.query(Course).filter(Course.id == course_id).first()
    if not row:
        raise BusinessException(message="课程不存在")
    payload = data.model_dump(exclude_none=True)  # 前端none或不传就不更新
    if "name" in payload:
        payload["name"] = payload["name"].strip()
    if "code" in payload:
        code = payload["code"].strip()
        conflict = (
            db.query(Course).filter(Course.code == code, Course.id != course_id).first()
        )
        if conflict:
            raise BusinessException(message="课程编号已存在")
        payload["code"] = code
    if "description" in payload:
        payload["description"] = payload["description"].strip()
    for field, value in payload.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return CourseResponse.model_validate(row)


def delete_course(db: Session, course_id: int):
    """删除课程"""
    row = db.query(Course).filter(Course.id == course_id).first()
    if not row:
        raise BusinessException(message="课程不存在")
    linked = db.query(Schedule.id).filter(Schedule.course_id == course_id).first()
    if linked:
        raise BusinessException(message="该课程已关联课表，无法删除")
    db.delete(row)
    db.commit()
