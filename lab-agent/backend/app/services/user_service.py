from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.user import User
from app.schemas.user import (
    PasswordUpdateRequest,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.utils.password import hash_password, verify_password


def get_user_info(user: User) -> UserResponse:
    """把当前用户对象转成响应模型（不含密码）。"""
    return UserResponse.model_validate(user)


def update_user_info(db: Session, user: User, data: UserUpdateRequest):
    """用户自己改资料：忽略 role/status，防止越权提升权限。"""
    # pydatic对象转换成字典#
    # data里面有值的更新到数据库 忽略没有值的
    user_dict = data.model_dump(exclude_none=True, exclude={"role", "status"})
    for field, value in user_dict.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def update_password(db: Session, user: User, data: PasswordUpdateRequest):
    """修改密码：先校验原密码，且新旧密码不能相同。"""
    if not verify_password(data.old_password, user.password):
        raise BusinessException(message="原密码错误")
    if data.old_password == data.new_password:
        raise BusinessException(message="原密码不能与新密码相同")
    user.password = hash_password(data.new_password)
    db.commit()


def get_user_page_list(
    db: Session, page: int, page_size: int, keywords: str | None = None
):
    """分页模糊分页列表"""
    # select * from user where keywords like '%张%'
    query = db.query(User)
    if keywords:
        query = query.filter(
            or_(User.username.ilike(f"%{keywords}%"), User.name.ilike(f"%{keywords}%"))
        )
    total = query.count()
    items = (
        query.order_by(User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PageResponse(
        list=[UserResponse.model_validate(item) for item in items], total=total
    )


def create_user(db: Session, data: UserCreateRequest):
    """管理员创建用户，账号唯一冲突时回滚并提示。"""
    exist = db.query(User).filter(User.username == data.username).first()
    if exist:
        raise BusinessException(message="账号已存在")

    user = User(
        username=data.username,
        password=hash_password(data.password),
        name=data.name,
        role=data.role,
        email=data.email,
        phone=data.phone,
        avatar=data.avatar,
        status=data.status,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # 并发兜底：检查和提交之间账号被其他人创建，唯一索引冲突
        db.rollback()
        raise BusinessException(message="账号已存在")
    db.refresh(user)
    return UserResponse.model_validate(user)


def update_user(db: Session, user_id: int, data: UserUpdateRequest):
    """管理员更新用户信息，只覆盖传了的字段。"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(message="用户不存在")
    payload = data.model_dump(exclude_none=True)

    for field, value in payload.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def delete_user(db: Session, user_id: int, current_user: User):
    """删除用户；不允许删除自己，否则管理员会把自己锁在系统外。"""
    if user_id == current_user.id:
        return BusinessException(message="不能删除当前登录的用户")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(message="用户不存在")

    db.delete(user)
    db.commit()
