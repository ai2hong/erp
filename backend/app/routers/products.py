"""
routers/products.py — 상품 API

GET /products/        상품 목록 (카테고리 필터, 검색)
GET /products/{id}    상품 상세
"""

from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_staff
from app.database import get_db
from app.models.product import Product, ProductCategory, SaleStatus
from app.models.staff import Staff

router = APIRouter(prefix="/products", tags=["상품"])


class ProductResponse(BaseModel):
    id: int
    category: str
    name: str
    barcode: Optional[str] = None
    normal_price: int
    device_discount_price: Optional[int] = None
    sale_status: str
    supplier: Optional[str] = None
    memo: Optional[str] = None

    class Config:
        from_attributes = True


class ProductDetailResponse(ProductResponse):
    cost_price: Optional[int] = None
    margin_rate: Optional[float] = None


@router.get("/", summary="상품 목록")
async def list_products(
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: Optional[str] = Query(None, description="카테고리 필터"),
    search: Optional[str] = Query(None, description="상품명 검색"),
    status: Optional[str] = Query(None, description="판매상태 필터"),
) -> List[ProductResponse]:
    q = select(Product).order_by(Product.category, Product.name)

    if category:
        q = q.where(Product.category == category)
    if search:
        q = q.where(Product.name.ilike(f"%{search}%"))
    if status:
        q = q.where(Product.sale_status == status)

    rows = (await db.scalars(q)).all()
    return [ProductResponse.model_validate(r) for r in rows]


@router.get("/{product_id}", summary="상품 상세")
async def get_product(
    product_id: int,
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProductDetailResponse:
    product = await db.scalar(select(Product).where(Product.id == product_id))
    if not product:
        raise HTTPException(404, "상품을 찾을 수 없습니다.")

    resp = ProductDetailResponse.model_validate(product)
    # 원가/마진은 총괄·사장만 열람
    from app.models.staff import StaffRole
    if current_staff.role not in (StaffRole.사장, StaffRole.총괄):
        resp.cost_price = None
        resp.margin_rate = None
    else:
        resp.margin_rate = product.margin_rate
    return resp
