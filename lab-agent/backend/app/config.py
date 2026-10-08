from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = (
    Path(__file__).parent.parent.joinpath(".env").resolve()
)  # 获取.env文件的绝对路径


class Settings(BaseSettings):
    DATABASE_URL: str
    model_dict = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8"
    )
