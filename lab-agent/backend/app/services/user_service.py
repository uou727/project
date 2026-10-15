from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserResponse, UserUpdateRequest


def get_user_info(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


def update_user_info(db: Session, user: User, data: UserUpdateRequest):
    # pydatic对象转换成字典#
    # data里面有值的更新到数据库 忽略没有值的
    user_dict = data.model_dump(exclude_none=True)
    for field, value in user_dict.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)
