from app.database import Base
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"comment": "用户信息表"}

    username: Mapped[str] = mapped_column(String(50), nullable=False, comment="用户名")
    password: Mapped[str] = mapped_column(String(50), nullable=False, comment="密码")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="姓名")
    role: Mapped[str] = mapped_column(String(50), nullable=False, comment="角色")
    email: Mapped[str | None] = mapped_column(String(50), comment="邮箱")
    phone: Mapped[str | None] = mapped_column(String(50), comment="电话")
    avatar: Mapped[str | None] = mapped_column(String(50), comment="头像")
    status: Mapped[int] = mapped_column(comment="状态0-禁用, 1-启用", default=1)
