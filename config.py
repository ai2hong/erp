import os
from dataclasses import dataclass


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass
class Config:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-only-change-me")
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "5000"))
    DEBUG: bool = os.getenv("FLASK_ENV", "production") == "development"
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    SESSION_COOKIE_SECURE: bool = _bool_env("SESSION_COOKIE_SECURE", False)
    JSON_AS_ASCII: bool = False
    MAX_CONTENT_LENGTH: int = 2 * 1024 * 1024  # 2MB for now
    ALLOWED_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:5000,http://localhost:5000").split(",")
        if origin.strip()
    ]
