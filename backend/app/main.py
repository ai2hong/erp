"""
main.py — VAPE DOG ERP FastAPI 앱 진입점

서버 실행:
  cd backend && uvicorn app.main:app --reload

API 문서 확인:
  http://localhost:8000/docs
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.database import create_tables

# 모델 전체 import — Alembic / create_tables 가 모든 테이블을 인식하도록
import app.models  # noqa: F401

# ── 라우터 import ─────────────────────────────────────────────
from app.routers.auth import router as auth_router
from app.routers.products import router as product_router
from app.routers.customers import router as customer_router
from app.routers.transactions import router as transaction_router
from app.routers.staff import router as staff_router
from app.routers.dayclose import router as dayclose_router


# ── 앱 시작/종료 이벤트 ───────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 {settings.APP_NAME} 서버 시작")
    if settings.DEBUG:
        await create_tables()
        print("✅ 테이블 확인 완료")
    yield
    print(f"👋 {settings.APP_NAME} 서버 종료")


# ── FastAPI 앱 생성 ───────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description="VAPE DOG ERP — 증산점·양산점·범어점",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── CORS 설정 ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 라우터 등록 ───────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(product_router)
app.include_router(customer_router)
app.include_router(transaction_router)
app.include_router(staff_router)
app.include_router(dayclose_router)


# ── 헬스체크 ─────────────────────────────────────────────────
@app.get("/", tags=["시스템"])
async def root():
    """서버 상태 확인."""
    return {
        "app": settings.APP_NAME,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["시스템"])
async def health():
    return {"status": "ok"}


# ── 정적 파일 (목업 UI) ────────────────────────────────────
_static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.isdir(_static_dir):
    app.mount("/ui", StaticFiles(directory=_static_dir, html=True), name="ui")
