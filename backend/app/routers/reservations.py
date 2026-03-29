"""
예약 주문 API
GET /reservations  — 전체 예약 목록
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.reservation import Reservation
from app.models.customer import Customer
from app.models.product import Product
from app.models.staff import Staff
from app.core.deps import get_current_staff

router = APIRouter()


@router.get("")
async def list_reservations(
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    result = await db.execute(
        select(Reservation, Customer, Product, Staff)
        .join(Customer, Reservation.customer_id == Customer.id)
        .outerjoin(Product, Reservation.product_id == Product.id)
        .outerjoin(Staff, Reservation.reserved_by == Staff.id)
        .where(Customer.is_deleted == False)
        .order_by(Reservation.created_at.desc())
        .limit(300)
    )
    rows = result.all()
    return [
        {
            "id":           r.id,
            "customer_id":  r.customer_id,
            "customer_name": c.name,
            "customer_phone": c.phone,
            "product_id":   r.product_id,
            "product_name": p.name if p else None,
            "quantity":     r.quantity,
            "status":       r.status,
            "note":         r.note,
            "created_at":   r.created_at,
            "staff_name":   s.name if s else None,
        }
        for r, c, p, s in rows
    ]
