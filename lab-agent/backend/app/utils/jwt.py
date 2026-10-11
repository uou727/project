from datetime import datetime, timedelta

import jwt

from app.config import settings


def create_access_token(user_id: int) -> str:
    """创建JWT token"""

    expire = datetime.now() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {"user_id": user_id, "exp": expire}
    token = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return token


def decode_access_token(token: str) -> dict:
    """解码JWT token"""

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
