"""
고객 API 라우터
GET  /customers/search  — 이름·전화번호 검색
GET  /customers/{id}    — 고객 단건 + 적립금
POST /customers         — 신규 등록
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.database import get_db
from app.models.customer import Customer
from app.core.deps import get_current_staff
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class CustomerCreate(BaseModel):
    name: str
    phone: str
    staff_memo: Optional[str] = None


@router.get("/search")
async def search_customer(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    result = await db.execute(
        select(Customer).where(
            Customer.is_deleted == False,
            or_(Customer.name.contains(q), Customer.phone.contains(q))
        ).limit(10)
    )
    customers = result.scalars().all()
    return [
        {
            "id": c.id, "name": c.name, "phone": c.phone,
            "mileage_balance": c.mileage_balance,
            "visit_count": c.visit_count,
            "last_visit_at": c.last_visit_at,
            "staff_memo": c.staff_memo,
        }
        for c in customers
    ]


@router.get("/{customer_id}")
async def get_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.is_deleted == False)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "고객을 찾을 수 없습니다")
    return {
        "id": c.id, "name": c.name, "phone": c.phone,
        "mileage_balance": c.mileage_balance,
        "visit_count": c.visit_count,
        "total_purchase": c.total_purchase,
        "last_visit_at": c.last_visit_at,
        "staff_memo": c.staff_memo,
    }


@router.post("")
async def create_customer(
    body: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    exists = await db.execute(
        select(Customer).where(Customer.phone == body.phone, Customer.is_deleted == False)
    )
    if exists.scalar_one_or_none():
        raise HTTPException(409, "이미 등록된 전화번호입니다")
    c = Customer(name=body.name, phone=body.phone, staff_memo=body.staff_memo)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return {"id": c.id, "name": c.name, "phone": c.phone, "mileage_balance": 0}
