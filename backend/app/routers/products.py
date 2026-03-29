"""
상품 API 라우터
GET /products           — 전체 상품 목록 (매장별 재고 포함)
GET /products/{id}      — 상품 단건
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.product import Product, SaleStatus
from app.core.deps import get_current_staff
from typing import Optional

router = APIRouter()


@router.get("")
async def get_products(
    store_id: int = Query(..., description="매장 ID"),
    category: Optional[str] = Query(None),
    sale_status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    q = select(Product).options(selectinload(Product.inventories))

    if category:
        q = q.where(Product.category == category)
    if sale_status:
        q = q.where(Product.sale_status == sale_status)
    else:
        q = q.where(Product.sale_status != SaleStatus.단종)

    q = q.order_by(Product.category, Product.name)
    result = await db.execute(q)
    products = result.scalars().all()

    return [
        {
            "id": p.id,
            "category": p.category,
            "name": p.name,
            "normal_price": p.normal_price,
            "device_discount_price": p.device_discount_price,
            "sale_status": p.sale_status,
            "stock": next(
                (
                    {
                        "qty_actual": i.qty_actual,
                        "qty_available": i.qty_available,
                        "is_shortage": i.is_shortage,
                        "is_out_of_stock": i.is_out_of_stock,
                    }
                    for i in p.inventories if i.store_id == store_id
                ),
                None,
            ),
        }
        for p in products
    ]


DEVICE_CATEGORIES = ["입호흡 기기", "입호흡 기기(단일가)", "폐호흡 기기", "폐호흡 기기(단일가)"]

@router.get("/search")
async def search_products(
    q: str = Query(..., min_length=1),
    device_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    stmt = select(Product).where(
        Product.name.contains(q),
        Product.sale_status != SaleStatus.단종,
    )
    if device_only:
        stmt = stmt.where(Product.category.in_(DEVICE_CATEGORIES))
    result = await db.execute(stmt.order_by(Product.name).limit(20))
    products = result.scalars().all()
    return [{"id": p.id, "name": p.name, "category": p.category} for p in products]


@router.get("/{product_id}")
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다")
    return p
