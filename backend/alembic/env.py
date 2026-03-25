"""
Alembic env.py — VAPE DOG ERP 마이그레이션 환경 설정

.env에서 DATABASE_URL을 읽어 동기 URL로 변환하여 사용.
asyncpg → psycopg2 드라이버로 자동 교체.
"""
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from dotenv import load_dotenv

# .env 로드
load_dotenv()

# Alembic Config
config = context.config

# 로깅 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# .env의 DATABASE_URL 사용 (async → sync 변환)
database_url = os.getenv("DATABASE_URL", "")
# asyncpg → psycopg2 변환 (alembic은 동기 드라이버 필요)
sync_url = database_url.replace("+asyncpg", "")
config.set_main_option("sqlalchemy.url", sync_url)

# 모든 모델 import → autogenerate가 테이블 인식
import app.models  # noqa: F401
from app.database import Base

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
