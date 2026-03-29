"""
재고 API 라우터
GET  /inventory         — 매장별 재고 목록
POST /inventory/inbound — 입고 처리
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, outerjoin
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.inventory import Inventory
from app.models.inventory_move import InventoryMove, MoveType
from app.models.product import Product, SaleStatus
from app.core.deps import get_current_staff
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


class InboundBody(BaseModel):
    store_id:   int
    product_id: int
    qty:        int
    memo:       str = ""


@router.get("")
async def get_inventory(
    store_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    # Product 기준 LEFT JOIN — 재고 레코드가 없는 상품도 포함
    stmt = (
        select(Product, Inventory)
        .select_from(
            outerjoin(
                Product,
                Inventory,
                (Inventory.product_id == Product.id) & (Inventory.store_id == store_id),
            )
        )
        .where(Product.sale_status != SaleStatus.단종)
        .order_by(Product.category, Product.name)
    )
    result = await db.execute(stmt)
    rows = result.all()

    out = []
    for product, inv in rows:
        qty      = inv.quantity       if inv else 0
        safety   = (inv.safety_stock or 0) if inv else 0
        shortage = (qty <= safety and safety > 0) if inv else False
        out.append({
            "id":               inv.id       if inv else None,
            "product_id":       product.id,
            "product_name":     product.name,
            "product_category": product.category,
            "qty_actual":       qty,
            "qty_available":    qty,
            "qty_undelivered":  0,
            "qty_reserved":     0,
            "safety_qty":       safety,
            "is_shortage":      shortage,
            "is_out_of_stock":  qty == 0,
            "last_inbound_at":  inv.updated_at if inv else None,
        })
    return out


@router.post("/inbound")
async def inbound(
    body: InboundBody,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    result = await db.execute(
        select(Inventory).where(
            Inventory.product_id == body.product_id,
            Inventory.store_id   == body.store_id,
        )
    )
    inv = result.scalar_one_or_none()

    if not inv:
        inv = Inventory(product_id=body.product_id, store_id=body.store_id, quantity=0)
        db.add(inv)
        await db.flush()

    before = inv.quantity
    inv.quantity += body.qty

    db.add(InventoryMove(
        product_id      = body.product_id,
        store_id        = body.store_id,
        move_type       = MoveType.입고,
        quantity        = body.qty,
        quantity_before = before,
        quantity_after  = inv.quantity,
        staff_id        = current_staff.id,
        note            = body.memo or None,
    ))

    await db.commit()
    return {"product_id": body.product_id, "qty_actual": inv.quantity}
