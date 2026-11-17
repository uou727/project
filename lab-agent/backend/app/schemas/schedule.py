from datetime import date

from pydantic import BaseModel, ConfigDict


class ScheduleCreateRequest(BaseModel):
    """管理员新增课表。"""

    user_id: int
    course_id: int
    class_date: date
    period: str
    location: str

    model_config = ConfigDict(str_strip_whitespace=True)


class ScheduleUpdateRequest(BaseModel):
    """管理员更新课表。"""

    user_id: int
    course_id: int
    class_date: date
    period: str
    location: str

    model_config = ConfigDict(str_strip_whitespace=True)


class ScheduleResponse(BaseModel):
    """课表返回（联表带出账号、姓名、课程名，方便页面和 AI 直接使用）

    class_date 必须是 date 类型：表里是 Date 列，service 传进来的也是 date 对象，
    声明成 str 会让 pydantic 抛 ValidationError，接口直接变 500。
    """

    id: int
    user_id: int
    course_id: int
    course_name: str | None = None
    class_date: date
    period: str
    start_time: str | None = None
    end_time: str | None = None
    location: str | None = None
    user_name: str | None = None
    username: str | None = None

    model_config = ConfigDict(from_attributes=True)
