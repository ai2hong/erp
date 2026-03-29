"""
미수령 API
GET /unpaid  — 전체 미수령 목록 (미이행 건)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.unpaid_service import UnpaidService
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.models.staff import Staff
from app.core.deps import get_current_staff

router = APIRouter()


@router.get("")
async def list_unpaid(
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    result = await db.execute(
        select(UnpaidService, Customer, Staff)
        .join(Customer, UnpaidService.customer_id == Customer.id)
        .outerjoin(Transaction, UnpaidService.transaction_id == Transaction.id)
        .outerjoin(Staff, Transaction.staff_id == Staff.id)
        .where(UnpaidService.is_fulfilled == False, Customer.is_deleted == False)
        .order_by(UnpaidService.created_at.desc())
        .limit(300)
    )
    rows = result.all()
    return [
        {
            "id":            u.id,
            "customer_id":   u.customer_id,
            "customer_name": c.name,
            "customer_phone": c.phone,
            "transaction_id": u.transaction_id,
            "service_type":  u.service_type,
            "quantity":      u.quantity,
            "note":          u.note,
            "is_fulfilled":  u.is_fulfilled,
            "created_at":    u.created_at,
            "staff_name":    s.name if s else None,
        }
        for u, c, s in rows
    ]
