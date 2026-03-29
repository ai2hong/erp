"""
app/core/config.py — VapeERP 설정

.env 파일에서 값을 읽어옴.
없으면 개발용 기본값 사용 (운영 환경에서는 반드시 .env 설정 필요).
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # DB
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/vape_erp"

    # JWT
    SECRET_KEY: str = "dev-secret-key-change-in-production-must-be-long-enough"
    REFRESH_SECRET_KEY: str = "dev-refresh-secret-key-change-in-production-too"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
