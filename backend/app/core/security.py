"""
core/security.py — VapeERP 인증 보안 유틸리티

포함:
  - 비밀번호 해싱 / 검증 (bcrypt rounds=12)
  - JWT Access 토큰 발급 / 검증  (만료: 30분)
  - JWT Refresh 토큰 발급 / 검증 (만료: 7일, 별도 시크릿)

미포함 (의도적 제외):
  - 비밀번호 강도 검증 (운영 정책상 불필요)
  - 로그인 실패 횟수 제한 (운영 정책상 불필요)

의존 패키지:
  pip install passlib[bcrypt] python-jose[cryptography]
"""

import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import settings   # SECRET_KEY, REFRESH_SECRET_KEY, ALGORITHM 등

# ── bcrypt 컨텍스트 ──────────────────────────────────────────
# rounds=12 → 브루트포스 연산 비용 증가 (기본값 10보다 강함)
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


# ══════════════════════════════════════════════
# 비밀번호
# ══════════════════════════════════════════════

def hash_password(plain: str) -> str:
    """평문 비밀번호 → bcrypt 해시. 호출 즉시 평문 파기."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    비밀번호 검증.
    passlib 내부적으로 constant-time 비교 → 타이밍 공격 방지.
    """
    return pwd_context.verify(plain, hashed)


# ══════════════════════════════════════════════
# JWT
# ══════════════════════════════════════════════

class TokenPayload(BaseModel):
    """디코딩된 토큰 페이로드."""
    sub:      int     # staff.id
    login_id: str
    role:     str
    store_id: int
    jti:      str     # 토큰 고유 ID (블랙리스트 / 세션 관리용)
    type:     str     # "access" | "refresh"


def _make_token(
    *,
    staff_id: int,
    login_id: str,
    role: str,
    store_id: int,
    token_type: str,
    expire_delta: timedelta,
    secret: str,
) -> str:
    """공통 JWT 생성 내부 함수."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub":      str(staff_id),
        "login_id": login_id,
        "role":     role,
        "store_id": store_id,
        "jti":      secrets.token_hex(16),   # 매번 고유값
        "type":     token_type,
        "iat":      now,
        "exp":      now + expire_delta,
    }
    return jwt.encode(payload, secret, algorithm=settings.ALGORITHM)


def create_access_token(staff_id: int, login_id: str, role: str, store_id: int) -> str:
    """
    Access 토큰 발급.
    만료: settings.ACCESS_TOKEN_EXPIRE_MINUTES (기본 30분)
    서명 키: settings.SECRET_KEY
    """
    return _make_token(
        staff_id=staff_id, login_id=login_id, role=role, store_id=store_id,
        token_type="access",
        expire_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        secret=settings.SECRET_KEY,
    )


def create_refresh_token(staff_id: int, login_id: str, role: str, store_id: int) -> str:
    """
    Refresh 토큰 발급.
    만료: settings.REFRESH_TOKEN_EXPIRE_DAYS (기본 7일)
    서명 키: settings.REFRESH_SECRET_KEY  ← Access 와 다른 키 사용
    """
    return _make_token(
        staff_id=staff_id, login_id=login_id, role=role, store_id=store_id,
        token_type="refresh",
        expire_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        secret=settings.REFRESH_SECRET_KEY,
    )


def _decode_token(token: str, secret: str, expected_type: str) -> TokenPayload:
    """공통 토큰 디코딩. 서명·만료·타입 불일치 시 ValueError."""
    try:
        raw = jwt.decode(token, secret, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise ValueError("유효하지 않거나 만료된 토큰입니다.")

    if raw.get("type") != expected_type:
        raise ValueError(f"{expected_type} 토큰이 아닙니다.")

    return TokenPayload(
        sub=int(raw["sub"]),
        login_id=raw["login_id"],
        role=raw["role"],
        store_id=raw["store_id"],
        jti=raw["jti"],
        type=raw["type"],
    )


def decode_access_token(token: str) -> TokenPayload:
    return _decode_token(token, settings.SECRET_KEY, "access")


def decode_refresh_token(token: str) -> TokenPayload:
    return _decode_token(token, settings.REFRESH_SECRET_KEY, "refresh")
