"""
app/core/config.py — 환경변수 설정

절대 이 파일에 실제 값을 적지 마세요.
모든 민감한 값은 .env 파일에서만 읽어옵니다.

.env 파일 위치: backend/.env  (절대 git에 올리지 마세요)
.env 파일 생성: cp .env.example .env  후 값 입력
"""
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    # 데이터베이스
    DATABASE_URL: str

    # JWT 토큰 — .env에서 반드시 설정 (openssl rand -hex 32 로 생성)
    SECRET_KEY: str
    REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 앱 설정
    APP_NAME: str = "VAPE DOG ERP"
    DEBUG: bool = False   # 운영 환경에서는 반드시 False

    @validator("SECRET_KEY", "REFRESH_SECRET_KEY")
    def key_must_be_set(cls, v):
        if not v or v in ("개발용_임시키_반드시_변경하세요", "change_me", "secret"):
            raise ValueError("SECRET_KEY는 .env 파일에서 실제 랜덤 값으로 설정해야 합니다. openssl rand -hex 32 로 생성하세요.")
        if len(v) < 32:
            raise ValueError("SECRET_KEY는 최소 32자 이상이어야 합니다.")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 전역 인스턴스
settings = Settings()
