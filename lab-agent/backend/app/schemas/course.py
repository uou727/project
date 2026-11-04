from pydantic import BaseModel, ConfigDict


class CourseCreateRequest(BaseModel):
    """新增课程的请求对象"""

    name: str
    code: str
    description: str | None = None
    status: int


class CourseUpdateRequest(BaseModel):
    """更新课程（可选）"""

    name: str
    code: str
    description: str | None = None
    status: int


class CourseResponse(BaseModel):
    """课程响应对象"""

    id: int
    name: str
    code: str
    description: str | None = None
    status: int

    model_config = ConfigDict(from_attributes=True)
