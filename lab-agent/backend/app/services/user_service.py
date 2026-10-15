from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.models.user import User
from app.schemas.user import PasswordUpdateRequest, UserResponse, UserUpdateRequest
from app.utils.password import hash_password, verify_password


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


def update_password(db: Session, user: User, data: PasswordUpdateRequest):
    if not verify_password(data.old_password, user.password):
        raise BusinessException(message="原密码错误")
    if data.old_password == data.new_password:
        raise BusinessException(message="原密码不能与新密码相同")
    user.password = hash_password(data.new_password)
    db.commit()
