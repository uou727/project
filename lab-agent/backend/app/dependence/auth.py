from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.database import get_db
from app.models.user import User
from app.utils.jwt import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

"""JWT 依赖模块，用于获取当前登录用户信息"""


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="登录失效请重新登录"
        )
    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的登陆凭证"
        )
    # 查询用户信息
    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户被禁用，请联系管理员"
        )
    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """判断JWT token内角色是否是admin"""
    print(current_user)
    if current_user.role != "admin":
        raise BusinessException(message="无访问权限", code=403)
    return current_user
