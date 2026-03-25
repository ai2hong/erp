"""
routers/staff.py — 직원 관리 API

GET /staff/        직원 목록
GET /staff/{id}    직원 상세
"""

from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_staff, RequireManager
from app.database import get_db
from app.models.staff import Staff, StaffRole, Store

router = APIRouter(prefix="/staff", tags=["직원"])


class StaffResponse(BaseModel):
    id: int
    name: str
    login_id: str
    role: str
    store_id: int
    store_name: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/", summary="직원 목록 [매니저 이상]")
async def list_staff(
    current_staff: Annotated[Staff, RequireManager],
    db: Annotated[AsyncSession, Depends(get_db)],
    store_id: Optional[int] = Query(None),
) -> List[StaffResponse]:
    q = (
        select(Staff)
        .options(selectinload(Staff.store))
        .order_by(Staff.store_id, Staff.name)
    )

    if store_id:
        if not current_staff.can_access_store(store_id):
            raise HTTPException(403, "해당 매장에 접근 권한이 없습니다.")
        q = q.where(Staff.store_id == store_id)

    rows = (await db.scalars(q)).all()
    return [
        StaffResponse(
            id=s.id,
            name=s.name,
            login_id=s.login_id,
            role=s.role,
            store_id=s.store_id,
            store_name=s.store.name if s.store else None,
            is_active=s.is_active,
        )
        for s in rows
    ]


@router.get("/{staff_id}", summary="직원 상세 [매니저 이상]")
async def get_staff(
    staff_id: int,
    current_staff: Annotated[Staff, RequireManager],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StaffResponse:
    staff = await db.scalar(
        select(Staff)
        .where(Staff.id == staff_id)
        .options(selectinload(Staff.store))
    )
    if not staff:
        raise HTTPException(404, "직원을 찾을 수 없습니다.")

    return StaffResponse(
        id=staff.id,
        name=staff.name,
        login_id=staff.login_id,
        role=staff.role,
        store_id=staff.store_id,
        store_name=staff.store.name if staff.store else None,
        is_active=staff.is_active,
    )
