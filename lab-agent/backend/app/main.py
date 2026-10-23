import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from app.api import api
from app.common.exceptions import (
    BusinessException,
    business_exception_handler,
    global_excpetion_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.config import UPLOAD_DIR
from app.database import Base, engine
from app.models.equipment import Equipment  # noqa

# 数据库表
from app.models.lab import Lab  # noqa
from app.models.reservation import Reservation  # noqa
from app.services import reservation_service

Base.metadata.create_all(bind=engine)  # 自动创建数据库和数据库的表


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动项目开启异步的扫描任务
    task = asyncio.create_task(reservation_service.run_expire_scan())
    yield
    task.cancel()  # 关闭项目同时取消异步任务


app = FastAPI(lifespan=lifespan)
"""跨域处理"""
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 允许的前端源，不要直接写 ["*"]
    allow_credentials=True,  # 关键：允许前端携带 Authorization token
    allow_methods=["*"],  # 允许所有请求方法 GET POST PUT DELETE OPTIONS
    allow_headers=["*"],  # 允许所有请求头（包含Authorization）
)
app.include_router(api)


# 注册异常处理器
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
# 全局的异常兜底，必须放在最后注册
app.add_exception_handler(Exception, global_excpetion_handler)

# 挂载静态文件目录      http://127.0.0.1:8000/uploads/xxx.jpg
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="upload")


@app.get("/")
def root():
    return {"message": "FastAPI is running!"}
