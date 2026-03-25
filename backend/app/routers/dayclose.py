"""
routers/dayclose.py — 일마감 API

GET   /dayclose/                일마감 목록
POST  /dayclose/                일마감 제출
PATCH /dayclose/{id}/approve    일마감 승인
"""

from typing import Annotated, Optional, List
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_staff, RequireManager, RequireGeneral
from app.database import get_db
from app.models.day_close import DayClose, DayCloseStatus
from app.models.staff import Staff

router = APIRouter(prefix="/dayclose", tags=["일마감"])


class DayCloseResponse(BaseModel):
    id: int
    close_date: date
    store_id: int
    status: str
    opening_cash: Optional[int] = None
    actual_cash: Optional[int] = None
    tx_count: int
    grand_total: int
    cash_diff: Optional[int] = None
    special_note: Optional[str] = None

    class Config:
        from_attributes = True


class DayCloseSubmitRequest(BaseModel):
    store_id: int
    close_date: date
    opening_cash: int = 0
    actual_cash: int
    special_note: Optional[str] = None


class DayCloseApproveRequest(BaseModel):
    approved: bool = True
    rejected_reason: Optional[str] = None


@router.get("/", summary="일마감 목록")
async def list_dayclose(
    current_staff: Annotated[Staff, RequireManager],
    db: Annotated[AsyncSession, Depends(get_db)],
    store_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
) -> List[DayCloseResponse]:
    q = select(DayClose).order_by(DayClose.close_date.desc())

    if store_id:
        if not current_staff.can_access_store(store_id):
            raise HTTPException(403, "해당 매장에 접근 권한이 없습니다.")
        q = q.where(DayClose.store_id == store_id)

    if date_from:
        q = q.where(DayClose.close_date >= date_from)
    if date_to:
        q = q.where(DayClose.close_date <= date_to)

    rows = (await db.scalars(q)).all()
    return [DayCloseResponse.model_validate(r) for r in rows]


@router.post("/", status_code=201, summary="일마감 제출 [매니저 이상]")
async def submit_dayclose(
    body: DayCloseSubmitRequest,
    current_staff: Annotated[Staff, RequireManager],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    if not current_staff.can_access_store(body.store_id):
        raise HTTPException(403, "해당 매장에 접근 권한이 없습니다.")

    # 중복 체크
    existing = await db.scalar(
        select(DayClose).where(
            DayClose.close_date == body.close_date,
            DayClose.store_id == body.store_id,
        )
    )
    if existing and existing.status != DayCloseStatus.미제출:
        raise HTTPException(409, "이미 제출된 일마감이 있습니다.")

    if existing:
        dc = existing
    else:
        dc = DayClose(
            close_date=body.close_date,
            store_id=body.store_id,
        )

    dc.opening_cash = body.opening_cash
    dc.actual_cash = body.actual_cash
    dc.special_note = body.special_note
    dc.status = DayCloseStatus.제출완료
    dc.submitted_by = current_staff.id
    dc.submitted_at = datetime.now(timezone.utc)

    # 현금 차이 계산
    dc.cash_diff = dc.actual_cash - ((dc.opening_cash or 0) + dc.total_cash)

    # TODO: 거래 집계 자동화 (tx_count, total_cash 등)

    if not existing:
        db.add(dc)
    await db.commit()
    await db.refresh(dc)
    return {"message": "일마감이 제출되었습니다.", "dayclose_id": dc.id}


@router.patch("/{dayclose_id}/approve", summary="일마감 승인/반려 [총괄·사장]")
async def approve_dayclose(
    dayclose_id: int,
    body: DayCloseApproveRequest,
    current_staff: Annotated[Staff, RequireGeneral],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    dc = await db.scalar(select(DayClose).where(DayClose.id == dayclose_id))
    if not dc:
        raise HTTPException(404, "일마감을 찾을 수 없습니다.")

    if dc.status != DayCloseStatus.제출완료:
        raise HTTPException(400, "제출 완료 상태의 일마감만 승인/반려할 수 있습니다.")

    if not current_staff.can_access_store(dc.store_id):
        raise HTTPException(403, "해당 매장에 접근 권한이 없습니다.")

    if body.approved:
        dc.status = DayCloseStatus.승인완료
    else:
        if not body.rejected_reason:
            raise HTTPException(400, "반려 사유는 필수입니다.")
        dc.status = DayCloseStatus.반려
        dc.rejected_reason = body.rejected_reason

    dc.approved_by = current_staff.id
    dc.approved_at = datetime.now(timezone.utc)

    await db.commit()
    return {"message": f"일마감이 {'승인' if body.approved else '반려'}되었습니다."}
