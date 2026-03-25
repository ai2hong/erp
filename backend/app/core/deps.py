"""
core/deps.py — FastAPI 의존성 주입 (Depends)

라우터 사용 예:
    # 로그인한 직원 누구나
    staff = Depends(get_current_staff)

    # 매니저 이상만
    staff = Depends(require_role(StaffRole.매니저))

    # 미리 정의된 단축 의존성
    staff: Staff = RequireAny       # 전 직원
    staff: Staff = RequireManager   # 매니저 이상
    staff: Staff = RequireGeneral   # 총괄 이상
    staff: Staff = RequireOwner     # 사장만

    # 매장 접근 체크 (역할 체크와 함께 사용)
    _: None = Depends(require_store_access())
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

# 역할 우선순위 (숫자 클수록 높은 권한)
ROLE_LEVEL = {
    StaffRole.판매사원: 1,
    StaffRole.매니저:   2,
    StaffRole.총괄:     3,
    StaffRole.사장:     4,
}


# ══════════════════════════════════════════════
# 기본 의존성 — 토큰 → Staff
# ══════════════════════════════════════════════

async def get_current_staff(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Staff:
    """
    Bearer 토큰 검증 후 Staff 반환.
    체크 순서:
      1. 토큰 서명 / 만료 검증
      2. JTI 블랙리스트 확인 (로그아웃된 토큰 차단)
      3. Staff 존재 확인
      4. is_active 확인
    """
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 블랙리스트 확인 (로그아웃된 토큰)
    blacklisted = await db.scalar(
        select(TokenBlacklist).where(TokenBlacklist.jti == payload.jti)
    )
    if blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이미 로그아웃된 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Staff 조회 (store_accesses eagerly load)
    staff = await db.scalar(
        select(Staff)
        .where(Staff.id == payload.sub)
        .options(selectinload(Staff.store_accesses))
    )
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="존재하지 않는 계정입니다.",
        )
    if not staff.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다. 관리자에게 문의하세요.",
        )

    return staff


# ══════════════════════════════════════════════
# 역할 기반 의존성
# ══════════════════════════════════════════════

def require_role(minimum_role: StaffRole):
    """
    지정 역할 이상만 허용.
    예) require_role(StaffRole.총괄) → 총괄·사장만 통과.
    """
    async def _guard(
        staff: Annotated[Staff, Depends(get_current_staff)],
    ) -> Staff:
        if ROLE_LEVEL.get(staff.role, 0) < ROLE_LEVEL[minimum_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"'{minimum_role}' 이상의 권한이 필요합니다.",
            )
        return staff
    return _guard


# 자주 쓰는 단축 의존성
RequireAny     = Depends(get_current_staff)
RequireManager = Depends(require_role(StaffRole.매니저))
RequireGeneral = Depends(require_role(StaffRole.총괄))
RequireOwner   = Depends(require_role(StaffRole.사장))


# ══════════════════════════════════════════════
# 매장 접근 의존성
# ══════════════════════════════════════════════

def require_store_access(store_id_param: str = "store_id"):
    """
    쿼리 파라미터 store_id 와 직원의 매장 접근 권한 대조.

    사용 예:
        @router.get("/transactions")
        async def list_tx(
            store_id: int = Query(...),
            staff: Staff = Depends(get_current_staff),
            _: None = Depends(require_store_access()),
        ):
    """
    async def _guard(
        store_id: Annotated[int, Query(alias=store_id_param)],
        staff: Annotated[Staff, Depends(get_current_staff)],
    ) -> None:
        if not staff.can_access_store(store_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"해당 매장에 접근 권한이 없습니다.",
            )
    return _guard
