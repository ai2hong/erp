"""
app/core/deps.py — FastAPI 의존성 주입

역할 레벨:
  관리자=5 > 사장=4 > 총괄=3 > 시니어=2 > 매니저=1

단축 의존성:
  RequireAny     — 전 직원 (로그인만 하면 됨)
  RequireSenior  — 시니어 이상 (구 RequireManager)
  RequireGeneral — 총괄 이상
  RequireOwner   — 사장 이상
  RequireAdmin   — 관리자만
"""
from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.security import decode_access_token
from app.database import get_db
from app.models.auth import TokenBlacklist
from app.models.staff import Staff, StaffRole

bearer_scheme = HTTPBearer(auto_error=True)

# 역할 우선순위
ROLE_LEVEL = {
    StaffRole.매니저: 1,
    StaffRole.시니어: 2,
    StaffRole.총괄:   3,
    StaffRole.사장:   4,
    StaffRole.관리자: 5,
}


async def get_current_staff(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Staff:
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e),
                            headers={"WWW-Authenticate": "Bearer"})

    blacklisted = await db.scalar(
        select(TokenBlacklist).where(TokenBlacklist.jti == payload.jti)
    )
    if blacklisted:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "이미 로그아웃된 토큰입니다.",
                            headers={"WWW-Authenticate": "Bearer"})

    staff = await db.scalar(
        select(Staff).where(Staff.id == payload.sub)
        .options(selectinload(Staff.store_accesses))
    )
    if not staff:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "존재하지 않는 계정입니다.")
    if not staff.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "비활성화된 계정입니다. 관리자에게 문의하세요.")

    return staff


def require_role(minimum_role: StaffRole):
    async def _guard(staff: Annotated[Staff, Depends(get_current_staff)]) -> Staff:
        if ROLE_LEVEL.get(staff.role, 0) < ROLE_LEVEL[minimum_role]:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                f"'{minimum_role}' 이상의 권한이 필요합니다.")
        return staff
    return _guard


# ── 단축 의존성 ───────────────────────────────────────────────
RequireAny     = Depends(get_current_staff)
RequireSenior  = Depends(require_role(StaffRole.시니어))   # 시니어 이상 (구 RequireManager)
RequireGeneral = Depends(require_role(StaffRole.총괄))     # 총괄 이상
RequireOwner   = Depends(require_role(StaffRole.사장))     # 사장 이상
RequireAdmin   = Depends(require_role(StaffRole.관리자))   # 관리자만


def require_store_access(store_id_param: str = "store_id"):
    async def _guard(
        store_id: Annotated[int, Query(alias=store_id_param)],
        staff: Annotated[Staff, Depends(get_current_staff)],
    ) -> None:
        if not staff.can_access_store(store_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "해당 매장에 접근 권한이 없습니다.")
    return _guard
