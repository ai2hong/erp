"""
app/database.py — 데이터베이스 연결 설정

SQLAlchemy 비동기 엔진 + 세션 설정.
모든 모델이 Base 를 상속받아야 테이블로 인식됨.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# ── DB 엔진 (연결 풀) ─────────────────────────────────────────
# echo=True → 실행되는 SQL을 터미널에 출력 (개발할 때 편함)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,      # 연결 끊김 자동 감지
    pool_size=10,
    max_overflow=20,
)

# ── 세션 팩토리 ───────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,   # commit 후에도 객체 속성 유지
)


# ── Base 클래스 ───────────────────────────────────────────────
# 모든 모델 파일에서 "from app.database import Base" 로 사용
class Base(DeclarativeBase):
    pass


# ── 의존성 주입용 세션 함수 ───────────────────────────────────
# FastAPI 라우터에서 Depends(get_db) 로 사용
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── 테이블 생성 함수 (개발 초기용) ───────────────────────────
# main.py의 startup 이벤트에서 한 번 호출
async def create_tables():
    """
    Alembic 없이 빠르게 테이블 생성.
    개발 초기에만 사용. 실제 운영은 alembic upgrade head 권장.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
