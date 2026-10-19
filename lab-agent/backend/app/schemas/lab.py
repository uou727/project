from pydantic import BaseModel, ConfigDict

# name: Mapped[str] = mapped_column(String(50), comment="名称", nullable=False)
# description: Mapped[str] = mapped_column(String(500), comment="简介")
# img: Mapped[str] = mapped_column(String(100), comment="封面")
# location: Mapped[str] = mapped_column(String(100), comment="位置")
# capacity: Mapped[int] = mapped_column(Integer, comment="容量", default=0)
# # 9：00 -18：00
# open_time: Mapped[str] = mapped_column(String(20), comment="开放开始时间")
# close_time: Mapped[str] = mapped_column(String(20), comment="开放结束时间")
# status: Mapped[int] = mapped_column(
#     Integer, comment="状态,0-关闭，1-开放", default=1


class LabResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    img: str | None = None
    location: str | None = None
    capacity: int
    open_time: str | None = None
    close_time: str | None = None
    status: int

    model_config = ConfigDict(from_attributes=True)


class LabCreateRequest(BaseModel):
    name: str
    description: str | None = None
    img: str | None = None
    location: str | None = None
    capacity: int
    open_time: str | None = None
    close_time: str | None = None
    status: int = 1


class LabUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    img: str | None = None
    location: str | None = None
    capacity: int | None = None
    open_time: str | None = None
    close_time: str | None = None
    status: int | None = None
