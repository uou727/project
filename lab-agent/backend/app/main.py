from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from app.api import api
from app.common.exceptions import (
    BusinessException,
    business_exception_handler,
    global_excpetion_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.database import Base, engine

Base.metadata.create_all(bind=engine)  # 自动创建数据库和数据库的表


app = FastAPI()
app.include_router(api)


# 注册异常处理器
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
# 全局的异常兜底，必须放在最后注册
app.add_exception_handler(Exception, global_excpetion_handler)


@app.get("/")
def root():
    return {"message": "FastAPI is running!"}
