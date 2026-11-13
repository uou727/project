from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StudyPlan(Base):
    __tablename__ = "study_plans"
    __table_args__ = {"comment": "学习计划信息"}

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), comment="学生ID", nullable=False
    )
    content: Mapped[str] = mapped_column(Text, comment="学习计划内容", nullable=False)
