"""
routers/customers.py — 고객 API

GET   /customers/               고객 목록
GET   /customers/{id}           고객 상세
POST  /customers/               고객 등록
PATCH /customers/{id}/mileage   적립금 수동 조정
"""

from typing import Annotated, Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_staff, RequireGeneral
from app.database import get_db
from app.models.customer import Customer
from app.models.mileage_ledger import MileageLedger, MileageType
from app.models.staff import Staff

router = APIRouter(prefix="/customers", tags=["고객"])


class CustomerResponse(BaseModel):
    id: int
    name: str
    phone: str
    mileage_balance: int
    last_visit_at: Optional[datetime] = None
    total_purchase: int
    visit_count: int
    visit_frequency_label: Optional[str] = None
    preferred_device: Optional[str] = None
    staff_memo: Optional[str] = None

    class Config:
        from_attributes = True


class CustomerCreateRequest(BaseModel):
    name: str
    phone: str
    staff_memo: Optional[str] = None
    preferred_liquid: Optional[str] = None
    preferred_nicotine: Optional[str] = None
    preferred_device: Optional[str] = None


class MileageAdjustRequest(BaseModel):
    amount: int
    note: str


@router.get("/", summary="고객 목록")
async def list_customers(
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: Optional[str] = Query(None, description="이름 또는 전화번호 검색"),
) -> List[CustomerResponse]:
    q = select(Customer).where(Customer.is_deleted == False).order_by(Customer.name)

    if search:
        q = q.where(
            (Customer.name.ilike(f"%{search}%")) |
            (Customer.phone.ilike(f"%{search}%"))
        )

    rows = (await db.scalars(q)).all()
    result = []
    for r in rows:
        resp = CustomerResponse.model_validate(r)
        resp.visit_frequency_label = r.visit_frequency_label
        result.append(resp)
    return result


@router.get("/{customer_id}", summary="고객 상세")
async def get_customer(
    customer_id: int,
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CustomerResponse:
    customer = await db.scalar(
        select(Customer).where(Customer.id == customer_id, Customer.is_deleted == False)
    )
    if not customer:
        raise HTTPException(404, "고객을 찾을 수 없습니다.")
    resp = CustomerResponse.model_validate(customer)
    resp.visit_frequency_label = customer.visit_frequency_label
    return resp


@router.post("/", status_code=201, summary="고객 등록")
async def create_customer(
    body: CustomerCreateRequest,
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    existing = await db.scalar(select(Customer).where(Customer.phone == body.phone))
    if existing:
        if existing.is_deleted:
            raise HTTPException(409, "삭제된 고객입니다. 관리자에게 문의하세요.")
        raise HTTPException(409, "이미 등록된 전화번호입니다.")

    customer = Customer(
        name=body.name,
        phone=body.phone,
        staff_memo=body.staff_memo,
        preferred_liquid=body.preferred_liquid,
        preferred_nicotine=body.preferred_nicotine,
        preferred_device=body.preferred_device,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return {"message": "고객이 등록되었습니다.", "customer_id": customer.id}


@router.patch("/{customer_id}/mileage", summary="적립금 수동 조정 [총괄·사장]")
async def adjust_mileage(
    customer_id: int,
    body: MileageAdjustRequest,
    current_staff: Annotated[Staff, RequireGeneral],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    customer = await db.scalar(
        select(Customer).where(Customer.id == customer_id, Customer.is_deleted == False)
    )
    if not customer:
        raise HTTPException(404, "고객을 찾을 수 없습니다.")

    if not body.note.strip():
        raise HTTPException(400, "조정 사유는 필수입니다.")

    new_balance = customer.mileage_balance + body.amount
    if new_balance < 0:
        raise HTTPException(400, f"잔액이 음수가 됩니다. 현재 잔액: {customer.mileage_balance:,}원")
    customer.mileage_balance = new_balance

    db.add(MileageLedger(
        customer_id=customer_id,
        mileage_type=MileageType.수동조정,
        amount=body.amount,
        balance_after=new_balance,
        note=body.note,
        staff_id=current_staff.id,
    ))

    await db.commit()
    return {
        "message": "적립금이 조정되었습니다.",
        "new_balance": new_balance,
    }
