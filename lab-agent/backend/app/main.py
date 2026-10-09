from app.database import Base, engine
from app.models.user import User as _User  # noqa
from fastapi import FastAPI

Base.metadata.create_all(bind=engine)  # 自动创建数据库和数据库的表

app = FastAPI()


@app.get("/")
def root():
    return {"message": "FastAPI is running!"}
