from pydantic import BaseModel, ConfigDict


class ScheduleCreateRequest(BaseModel):
    """管理员新增课表。"""

    user_id: int
    course_id: int
    class_date: str
    period: str
    location: str

    model_config = ConfigDict(str_strip_whitespace=True)


class ScheduleUpdateRequest(BaseModel):
    """管理员更新课表。"""

    user_id: int
    course_id: int
    class_date: str
    period: str
    location: str

    model_config = ConfigDict(str_strip_whitespace=True)


class ScheduleResponse(BaseModel):
    """课表返回（联表带出账号、姓名、课程名，方便页面直接展示）"""

    id: int
    user_id: int
    course_id: int
    class_date: str
    period: str
    location: str

    model_config = ConfigDict(from_attributes=True)
