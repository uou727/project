from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.course import Course
from app.models.schedule import Schedule
from app.models.user import User
from app.schemas.schedule import (
    ScheduleCreateRequest,
    ScheduleResponse,
    ScheduleUpdateRequest,
)

WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 节次对应的时间段。课表里只存「1-2节」这样的文本，
# 要做「哪些时间有空」的推导就必须有一份映射；不同学校作息不同，后续可以抽成配置表。
PERIOD_SLOTS: dict[str, tuple[str, str]] = {
    "1-2节": ("08:00", "09:40"),
    "3-4节": ("10:00", "11:40"),
    "5-6节": ("14:00", "15:40"),
    "7-8节": ("16:00", "17:40"),
    "9-10节": ("19:00", "20:40"),
}

# 一次查询最多覆盖的天数，防止 AI 传一个超长区间把接口拖垮
MAX_RANGE_DAYS = 31


def _as_date(value: date | str) -> date:
    """把 date 或 'YYYY-MM-DD' 字符串统一转成 date。

    表里 class_date 现在已经是 DATE 列，但历史库/手工导入的数据可能是字符串，
    统一在这里收口，避免下游调用 .weekday()、.strftime() 时抛 AttributeError。
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value).strip()[:10])


def _base_query(
    db: Session, user_id: int | None = None, class_date: date | None = None
):
    """课表基础查询：联表带出账号、姓名、课程名，供列表和单条响应复用。"""
    query = (
        db.query(Schedule, User.username, User.name, Course.name)
        .join(User, Schedule.user_id == User.id)
        .join(Course, Schedule.course_id == Course.id)
    )

    if user_id:
        query = query.filter(Schedule.user_id == user_id)

    if class_date:
        query = query.filter(Schedule.class_date == class_date)

    return query


def _to_response(
    row: Schedule,
    username: str,
    user_name: str,
    course_name: str,
) -> ScheduleResponse:
    """把 ORM 行转成响应模型，顺带按节次补上起止时间。"""
    start_time, end_time = PERIOD_SLOTS.get(row.period, (None, None))
    return ScheduleResponse(
        id=row.id,
        user_id=row.user_id,
        course_id=row.course_id,
        course_name=course_name,
        class_date=_as_date(row.class_date),
        period=row.period,
        start_time=start_time,
        end_time=end_time,
        location=row.location,
        user_name=user_name,
        username=username,
    )


def list_page_schedules(
    db: Session,
    user_id: int | None = None,
    class_date: date | None = None,
    page: int = 1,
    page_size: int = 10,
):
    """分页模糊查询课表列表"""
    query = _base_query(db, user_id, class_date)
    total = query.count()
    rows = (
        query.order_by(Schedule.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PageResponse(
        list=[
            _to_response(
                row=row, username=username, user_name=user_name, course_name=course_name
            )
            for row, username, user_name, course_name in rows
        ],
        total=total,
    )


def create_schedule(db: Session, data: ScheduleCreateRequest) -> ScheduleResponse:
    """新增课表"""
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise BusinessException(message="用户不存在")
    if user.role != "student":
        raise BusinessException(message="用户不是学生，不能排课")
    course = db.query(Course).filter(Course.id == data.course_id).first()

    if not course:
        raise BusinessException(message="课程不存在")
    row = Schedule(**data.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_response(
        row=row, username=user.username, user_name=user.name, course_name=course.name
    )


def update_schedule(
    db: Session, schedule_id: int, data: ScheduleUpdateRequest
) -> ScheduleResponse:
    """更新课表"""
    row = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not row:
        raise BusinessException(message="课表不存在")
    payload = data.model_dump(exclude_none=True)
    user_id = payload.get("user_id", row.user_id)
    course_id = payload.get("course_id", row.course_id)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(message="用户不存在")
    if user.role != "student":
        raise BusinessException(message="只能给学生安排课表")
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise BusinessException(message="课程不存在")
    for field, value in payload.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return _to_response(row, user.username, user.name, course.name)


def delete_schedule(db: Session, schedule_id: int) -> None:
    """删除课表"""
    row = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not row:
        raise BusinessException(message="课表不存在")
    db.delete(row)
    db.commit()


def _check_range(start_date: date, end_date: date) -> None:
    """校验查询区间，避免 AI 传一个夸张的范围把接口拖垮"""
    if end_date < start_date:
        raise BusinessException(message="结束日期不能早于开始日期")
    if (end_date - start_date).days > MAX_RANGE_DAYS:
        raise BusinessException(message=f"查询区间不能超过{MAX_RANGE_DAYS}天")


def list_schedules_in_range(
    db: Session, user_id: int, start_date: date, end_date: date
) -> list[dict]:
    """查询某人在日期区间内的全部课表，返回扁平字典供 AI 工具直接使用"""
    _check_range(start_date, end_date)
    rows = (
        db.query(Schedule, Course.name)
        .join(Course, Schedule.course_id == Course.id)
        .filter(
            Schedule.user_id == user_id,
            Schedule.class_date >= start_date,
            Schedule.class_date <= end_date,
        )
        .order_by(Schedule.class_date, Schedule.id)
        .all()
    )
    result = []
    for row, course_name in rows:
        start_time, end_time = PERIOD_SLOTS.get(row.period, (None, None))
        class_date = _as_date(row.class_date)
        result.append(
            {
                "date": class_date.strftime("%Y-%m-%d"),
                "weekday": WEEKDAY_NAMES[class_date.weekday()],
                "period": row.period,
                "start_time": start_time,
                "end_time": end_time,
                "course_name": course_name,
                "location": row.location,
            }
        )
    return result


def find_free_slots(
    db: Session, user_id: int, start_date: date, end_date: date
) -> list[dict]:
    """按天算出没课的时间段，供学习规划参考。

    空闲判断基于 PERIOD_SLOTS 里的标准节次；课表里若出现未知节次，
    会放进 unknown_periods 一起回传，让上层知道那天的时间其实没算全。
    """
    _check_range(start_date, end_date)
    schedules = list_schedules_in_range(db, user_id, start_date, end_date)

    busy_by_date: dict[str, set[str]] = {}
    unknown_by_date: dict[str, list[str]] = {}
    for item in schedules:
        busy_by_date.setdefault(item["date"], set()).add(item["period"])
        if item["period"] not in PERIOD_SLOTS:
            unknown_by_date.setdefault(item["date"], []).append(item["period"])

    result = []
    day = start_date
    while day <= end_date:
        key = day.strftime("%Y-%m-%d")
        busy = busy_by_date.get(key, set())
        free_periods = [p for p in PERIOD_SLOTS if p not in busy]
        result.append(
            {
                "date": key,
                "weekday": WEEKDAY_NAMES[day.weekday()],
                "free_periods": free_periods,
                "free_slots": [
                    {
                        "period": p,
                        "start_time": PERIOD_SLOTS[p][0],
                        "end_time": PERIOD_SLOTS[p][1],
                    }
                    for p in free_periods
                ],
                "busy_periods": sorted(busy),
                "unknown_periods": unknown_by_date.get(key, []),
            }
        )
        day += timedelta(days=1)
    return result
