from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.files import router as files_router
from app.api.lab import router as lab_router
from app.api.user import router as user_router

api = APIRouter(prefix="/api", tags=["API模块"])
api.include_router(user_router)
api.include_router(lab_router)
api.include_router(auth_router)
api.include_router(files_router)
