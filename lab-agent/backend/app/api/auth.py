from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import loginResponse
from app.schemas.user import UserResponse

router = APIRouter(prefix="/api/auth", tags=["权限验证模块"])


@router.post("/login")
def login(data: loginResponse, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()

    print("前端传的username:", data.username)
    print("前端传的password:", data.password)
    if user:
        print("数据库查到user的username:", user.username)
        print("数据库查到user的password:", user.password)
    else:
        print("数据库没有查到该用户！")

    # 判断账号密码是否正确
    if not user or user.password != data.password:
        return {"code": 400, "message": "账号或密码错误2"}

    return {
        "code": 200,
        "message": "登录成功",
        "data": UserResponse.model_validate(user),
    }
    # raise HTTPException(status_code=404, detail="User not found")

    # return loginResponse(
    #     username="test",
    #     password="test",
    #     access_token="test",
    #     token_type="bearer",
    # )
