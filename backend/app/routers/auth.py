"""
routers/auth.py — VapeERP 인증 API

엔드포인트:
  POST /auth/register             직원 가입 신청
  POST /auth/login                로그인 → Access + Refresh 토큰
  POST /auth/refresh              Access 토큰 갱신
  POST /auth/logout               로그아웃
  GET  /auth/me                   내 정보

  GET  /auth/admin/requests       가입 신청 목록    [총괄·사장]
  POST /auth/admin/approve        가입 신청 승인    [총괄·사장]
  POST /auth/admin/reject         가입 신청 반려    [총괄·사장]

적용된 보안:
  ✓ bcrypt(rounds=12) 해싱 — 평문 즉시 파기
  ✓ 로그인 이력 저장 (성공·실패·강제로그아웃)
  ✓ 중복 로그인 차단 — 1계정 1기기 세션
  ✓ Refresh 토큰 rotate — 갱신 시 새 JTI, 이전 JTI 블랙리스트
  ✓ 로그아웃 시 JTI 블랙리스트 등록
  ✓ 가입 승인 권한 제한 (총괄은 담당 매장만 / 자신보다 높은 역할 부여 불가)
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import re

from app.core.deps import get_current_staff, RequireGeneral
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.core.config import settings
from app.database import get_db
from app.models.auth import (
    LoginHistory, LoginResult,
    RegistrationStatus, StaffRegistrationRequest,
    StaffSession, TokenBlacklist,
)
from app.models.staff import Staff, StaffRole, StaffStoreAccess, Store

router = APIRouter(prefix="/auth", tags=["인증"])


# ── IP 추출 헬퍼 ─────────────────────────────────────────────
def _get_ip(request: Request) -> str:
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ══════════════════════════════════════════════
# 요청/응답 스키마
# ══════════════════════════════════════════════

class RegisterRequest(BaseModel):
    name:     str
    login_id: str
    password: str
    store_id: int
    memo:     Optional[str] = None

    @field_validator("login_id")
    @classmethod
    def validate_login_id(cls, v: str) -> str:
        v = v.strip()
        if not (4 <= len(v) <= 50):
            raise ValueError("아이디는 4~50자여야 합니다.")
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("아이디는 영문·숫자·밑줄(_)만 사용 가능합니다.")
        return v


class LoginRequest(BaseModel):
    login_id: str
    password: str


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    name:          str
    role:          str
    store_id:      int


class RefreshRequest(BaseModel):
    refresh_token: str


class ApproveRequest(BaseModel):
    request_id:   int
    role_granted: StaffRole = StaffRole.판매사원
    store_id:     Optional[int] = None   # None 이면 신청 매장 그대로 사용


class RejectRequest(BaseModel):
    request_id: int
    reason:     str


class MeResponse(BaseModel):
    id:         int
    name:       str
    login_id:   str
    role:       str
    store_id:   int
    store_name: Optional[str] = None


# ══════════════════════════════════════════════
# 가입 신청
# ══════════════════════════════════════════════

@router.post("/register", status_code=201, summary="직원 가입 신청")
async def register(
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    누구나 접근 가능 (미인증).
    비밀번호는 bcrypt 해싱 후 저장 — 평문은 이 시점에 파기.
    승인 전까지 로그인 불가.
    """
    # 매장 존재 확인
    store = await db.scalar(
        select(Store).where(Store.id == body.store_id, Store.is_active == True)
    )
    if not store:
        raise HTTPException(400, "존재하지 않는 매장입니다.")

    # login_id 중복: staff 테이블
    if await db.scalar(select(Staff).where(Staff.login_id == body.login_id)):
        raise HTTPException(409, "이미 사용 중인 아이디입니다.")

    # login_id 중복: 대기 중 신청 테이블
    if await db.scalar(
        select(StaffRegistrationRequest).where(
            StaffRegistrationRequest.login_id == body.login_id,
            StaffRegistrationRequest.status == RegistrationStatus.대기,
        )
    ):
        raise HTTPException(409, "동일 아이디로 승인 대기 중인 신청이 있습니다.")

    db.add(StaffRegistrationRequest(
        name=body.name,
        login_id=body.login_id,
        hashed_password=hash_password(body.password),  # ← 평문 즉시 해싱
        store_id=body.store_id,
        memo=body.memo,
    ))
    await db.commit()
    return {"message": "가입 신청이 접수되었습니다. 관리자 승인 후 로그인하실 수 있습니다."}


# ══════════════════════════════════════════════
# 로그인
# ══════════════════════════════════════════════

@router.post("/login", summary="로그인")
async def login(
    body: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    ⚠️  운영 환경 배포 전 필수 추가 사항:
        slowapi 또는 nginx rate limit 으로 IP당 로그인 시도를 제한하세요.
        예시: pip install slowapi → @limiter.limit("5/minute") 데코레이터 적용
        미적용 시 브루트포스 공격에 노출됩니다.

    로그인 처리 순서:
      1. 비밀번호 검증 (실패 시 이력 저장)
      2. 기존 세션 강제 만료 → 강제로그아웃 이력 저장
      3. 새 세션 등록 + 토큰 발급
      4. 성공 이력 저장
    """
    ip = _get_ip(request)
    ua = request.headers.get("User-Agent", "")[:512]

    # 1. Staff 조회 + 비밀번호 검증
    staff = await db.scalar(
        select(Staff)
        .where(Staff.login_id == body.login_id)
        .options(selectinload(Staff.store_accesses))
    )

    if not staff or not verify_password(body.password, staff.hashed_password):
        # 실패 이력 저장
        db.add(LoginHistory(
            staff_id=staff.id if staff else None,
            login_id=body.login_id,
            result=LoginResult.실패,
            ip_address=ip,
            user_agent=ua,
        ))
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다.",
        )

    if not staff.is_active:
        raise HTTPException(403, "비활성화된 계정입니다. 관리자에게 문의하세요.")

    # 2. 기존 세션 강제 만료 (중복 로그인 차단)
    old_session = await db.scalar(
        select(StaffSession).where(StaffSession.staff_id == staff.id)
    )
    if old_session:
        # 이전 Refresh JTI 블랙리스트
        db.add(TokenBlacklist(
            jti=old_session.refresh_jti,
            staff_id=staff.id,
            token_type="refresh",
            expires_at=old_session.expires_at,
        ))
        await db.delete(old_session)
        # 강제로그아웃 이력
        db.add(LoginHistory(
            staff_id=staff.id,
            login_id=staff.login_id,
            result=LoginResult.강제로그아웃,
            ip_address=ip,
            user_agent=ua,
        ))
        await db.flush()

    # 3. 새 토큰 발급
    access_token  = create_access_token(staff.id, staff.login_id, staff.role, staff.store_id)
    refresh_token = create_refresh_token(staff.id, staff.login_id, staff.role, staff.store_id)
    rt_payload    = decode_refresh_token(refresh_token)

    db.add(StaffSession(
        staff_id=staff.id,
        refresh_jti=rt_payload.jti,
        ip_address=ip,
        user_agent=ua,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    ))

    # 4. 성공 이력 + last_login_at 갱신
    db.add(LoginHistory(
        staff_id=staff.id,
        login_id=staff.login_id,
        result=LoginResult.성공,
        ip_address=ip,
        user_agent=ua,
    ))
    staff.last_login_at = datetime.now(timezone.utc)

    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        name=staff.name,
        role=staff.role,
        store_id=staff.store_id,
    )


# ══════════════════════════════════════════════
# 토큰 갱신 (Refresh Rotate)
# ══════════════════════════════════════════════

@router.post("/refresh", summary="Access 토큰 갱신")
async def refresh(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Refresh 토큰으로 새 Access + Refresh 발급.
    이전 Refresh JTI → 블랙리스트 등록 (Refresh Rotate).
    탈취된 토큰이 재사용되면 세션 불일치로 차단됨.
    """
    try:
        payload = decode_refresh_token(body.refresh_token)
    except ValueError as e:
        raise HTTPException(401, str(e))

    # 블랙리스트 확인
    if await db.scalar(select(TokenBlacklist).where(TokenBlacklist.jti == payload.jti)):
        raise HTTPException(401, "이미 만료된 Refresh 토큰입니다.")

    # 세션 JTI 일치 확인
    session = await db.scalar(
        select(StaffSession).where(
            StaffSession.staff_id == payload.sub,
            StaffSession.refresh_jti == payload.jti,
        )
    )
    if not session:
        raise HTTPException(401, "유효하지 않은 세션입니다. 다시 로그인해주세요.")

    staff = await db.scalar(select(Staff).where(Staff.id == payload.sub))
    if not staff or not staff.is_active:
        raise HTTPException(403, "접근 불가 계정입니다.")

    # 이전 JTI 블랙리스트
    db.add(TokenBlacklist(
        jti=payload.jti,
        staff_id=staff.id,
        token_type="refresh",
        expires_at=session.expires_at,
    ))

    # 새 토큰 발급 + 세션 JTI 교체
    new_access  = create_access_token(staff.id, staff.login_id, staff.role, staff.store_id)
    new_refresh = create_refresh_token(staff.id, staff.login_id, staff.role, staff.store_id)
    new_rt_pl   = decode_refresh_token(new_refresh)

    session.refresh_jti = new_rt_pl.jti
    session.expires_at  = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    await db.commit()

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        name=staff.name,
        role=staff.role,
        store_id=staff.store_id,
    )


# ══════════════════════════════════════════════
# 로그아웃
# ══════════════════════════════════════════════

@router.post("/logout", status_code=204, summary="로그아웃")
async def logout(
    body: RefreshRequest,
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    세션 삭제 + Refresh JTI 블랙리스트 등록.
    Access 토큰은 짧은 만료(30분)로 자연 소멸.
    """
    try:
        rt_payload = decode_refresh_token(body.refresh_token)
    except ValueError:
        return  # 이미 만료된 토큰이면 그냥 통과

    session = await db.scalar(
        select(StaffSession).where(StaffSession.staff_id == current_staff.id)
    )
    if session:
        db.add(TokenBlacklist(
            jti=rt_payload.jti,
            staff_id=current_staff.id,
            token_type="refresh",
            expires_at=session.expires_at,
        ))
        await db.delete(session)
        await db.commit()


# ══════════════════════════════════════════════
# 내 정보
# ══════════════════════════════════════════════

@router.get("/me", summary="내 정보 조회")
async def me(
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MeResponse:
    store = await db.scalar(select(Store).where(Store.id == current_staff.store_id))
    return MeResponse(
        id=current_staff.id,
        name=current_staff.name,
        login_id=current_staff.login_id,
        role=current_staff.role,
        store_id=current_staff.store_id,
        store_name=store.name if store else None,
    )


# ══════════════════════════════════════════════
# 관리자 전용 — 가입 신청 관리
# ══════════════════════════════════════════════

@router.get("/admin/requests", summary="가입 신청 목록 [총괄·사장]")
async def list_requests(
    current_staff: Annotated[Staff, RequireGeneral],
    db: Annotated[AsyncSession, Depends(get_db)],
    filter_status: Optional[RegistrationStatus] = Query(None, alias="status"),
) -> List[dict]:
    """
    총괄: 담당 매장 신청만 조회.
    사장: 전체 조회.
    """
    q = (
        select(StaffRegistrationRequest)
        .options(selectinload(StaffRegistrationRequest.store))
        .order_by(StaffRegistrationRequest.created_at.desc())
    )
    if filter_status:
        q = q.where(StaffRegistrationRequest.status == filter_status)
    if current_staff.role == StaffRole.총괄:
        allowed = [a.store_id for a in current_staff.store_accesses]
        q = q.where(StaffRegistrationRequest.store_id.in_(allowed))

    rows = (await db.scalars(q)).all()
    return [
        {
            "id":          r.id,
            "name":        r.name,
            "login_id":    r.login_id,
            "store_id":    r.store_id,
            "store_name":  r.store.name if r.store else None,
            "status":      r.status,
            "memo":        r.memo,
            "reviewed_by": r.reviewed_by,
            "created_at":  r.created_at,
        }
        for r in rows
    ]


@router.post("/admin/approve", status_code=201, summary="가입 신청 승인 [총괄·사장]")
async def approve(
    body: ApproveRequest,
    current_staff: Annotated[Staff, RequireGeneral],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    승인 → Staff 레코드 자동 생성.

    권한 제한:
      - 총괄: 담당 매장 신청만 처리 가능
      - 총괄: 사장·총괄 역할 부여 불가 (자신보다 높은 역할 금지)
    """
    req = await db.scalar(
        select(StaffRegistrationRequest).where(
            StaffRegistrationRequest.id == body.request_id,
            StaffRegistrationRequest.status == RegistrationStatus.대기,
        )
    )
    if not req:
        raise HTTPException(404, "대기 중인 신청을 찾을 수 없습니다.")

    # 총괄 접근 범위 검사
    if current_staff.role == StaffRole.총괄:
        allowed = [a.store_id for a in current_staff.store_accesses]
        if req.store_id not in allowed:
            raise HTTPException(403, "담당 매장 외 신청은 처리할 수 없습니다.")
        if body.role_granted in (StaffRole.사장, StaffRole.총괄):
            raise HTTPException(403, "총괄 이상의 역할은 사장만 부여할 수 있습니다.")

    target_store = body.store_id or req.store_id

    # Staff 생성 (해싱된 비밀번호 그대로 이전)
    new_staff = Staff(
        store_id=target_store,
        name=req.name,
        login_id=req.login_id,
        hashed_password=req.hashed_password,
        role=body.role_granted,
        is_active=True,
    )
    db.add(new_staff)
    await db.flush()

    # 총괄·매니저면 StaffStoreAccess 행 생성
    if body.role_granted in (StaffRole.총괄, StaffRole.매니저):
        db.add(StaffStoreAccess(staff_id=new_staff.id, store_id=target_store))

    # 신청 상태 업데이트
    req.status           = RegistrationStatus.승인
    req.reviewed_by      = current_staff.id
    req.reviewed_at      = datetime.now(timezone.utc)
    req.created_staff_id = new_staff.id

    await db.commit()
    return {
        "message":          "승인 완료. 계정이 생성되었습니다.",
        "created_staff_id": new_staff.id,
        "login_id":         new_staff.login_id,
        "role":             new_staff.role,
    }


@router.post("/admin/reject", summary="가입 신청 반려 [총괄·사장]")
async def reject(
    body: RejectRequest,
    current_staff: Annotated[Staff, RequireGeneral],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    반려 사유 기록 후 해싱된 비밀번호 삭제 (개인정보 최소 보관).
    """
    req = await db.scalar(
        select(StaffRegistrationRequest).where(
            StaffRegistrationRequest.id == body.request_id,
            StaffRegistrationRequest.status == RegistrationStatus.대기,
        )
    )
    if not req:
        raise HTTPException(404, "대기 중인 신청을 찾을 수 없습니다.")

    if current_staff.role == StaffRole.총괄:
        allowed = [a.store_id for a in current_staff.store_accesses]
        if req.store_id not in allowed:
            raise HTTPException(403, "담당 매장 외 신청은 처리할 수 없습니다.")

    req.status          = RegistrationStatus.반려
    req.reviewed_by     = current_staff.id
    req.reviewed_at     = datetime.now(timezone.utc)
    req.rejected_reason = body.reason
    req.hashed_password = ""   # 반려 시 해시 삭제

    await db.commit()
    return {"message": "신청이 반려되었습니다.", "reason": body.reason}
