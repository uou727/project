from datetime import datetime

from app.config import settings
from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

engine = create_engine(settings.DATABASE_URL)

# 数据库session会话的连接工厂
SessionLocal = sessionmaker(engine=create_engine, autoflush=False)


def get_db():
    """
    获取数据库连接
    :return:
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="主键id"
    )
    create_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        comment="创建时间",
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime,
        onupdate=datetime.now,
        comment="更新时间",
    )
