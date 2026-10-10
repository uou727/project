from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.database import Base, engine
from app.models.user import User as _User  # noqa

Base.metadata.create_all(bind=engine)  # 自动创建数据库和数据库的表

app = FastAPI()
app.include_router(auth_router)


@app.get("/")
def root():
    return {"message": "FastAPI is running!"}
