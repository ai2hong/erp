"""
routers/products.py — 상품 API

GET /products/        상품 목록 (카테고리 필터, 검색, 페이지네이션)
GET /products/{id}    상품 상세
"""

from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_staff
from app.database import get_db
from app.models.product import Product, ProductCategory, SaleStatus, LIQUID_EXCL
from app.models.staff import Staff, StaffRole

router = APIRouter(prefix="/products", tags=["상품"])

# 이벤트 단가 매핑
_EVENT_PRICE_MAP = {
    ProductCategory.입호흡_이벤트: 20_000,
    ProductCategory.폐호흡_이벤트: 25_000,
}


class ProductResponse(BaseModel):
    id: int
    category: str
    name: str
    barcode: Optional[str] = None
    normal_price: int
    discount_price: Optional[int] = None
    event_price: Optional[int] = None
    cost_price: Optional[int] = None
    sale_status: str
    supplier: Optional[str] = None
    memo: Optional[str] = None
    is_excl: bool = False

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    items: List[ProductResponse]
    total: int
    page: int
    size: int
    pages: int


class ProductDetailResponse(ProductResponse):
    margin_rate: Optional[float] = None


def _to_response(product: Product, *, show_cost: bool = False) -> ProductResponse:
    """Product ORM → ProductResponse 변환."""
    cat = product.category
    return ProductResponse(
        id=product.id,
        category=product.category.value if isinstance(product.category, ProductCategory) else str(product.category),
        name=product.name,
        barcode=product.barcode,
        normal_price=product.normal_price,
        discount_price=product.device_discount_price,
        event_price=_EVENT_PRICE_MAP.get(cat),
        cost_price=product.cost_price if show_cost else None,
        sale_status=product.sale_status.value if isinstance(product.sale_status, SaleStatus) else str(product.sale_status),
        supplier=product.supplier,
        memo=product.memo,
        is_excl=cat in LIQUID_EXCL,
    )


@router.get("/", summary="상품 목록")
async def list_products(
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: Optional[str] = Query(None, description="카테고리 필터"),
    search: Optional[str] = Query(None, description="상품명 검색"),
    status: Optional[str] = Query(None, description="판매상태 필터"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(50, ge=1, le=200, description="페이지당 개수"),
) -> ProductListResponse:
    q = select(Product).order_by(Product.category, Product.name)
    count_q = select(sa_func.count(Product.id))

    if category:
        q = q.where(Product.category == category)
        count_q = count_q.where(Product.category == category)
    if search:
        q = q.where(Product.name.ilike(f"%{search}%"))
        count_q = count_q.where(Product.name.ilike(f"%{search}%"))
    if status:
        q = q.where(Product.sale_status == status)
        count_q = count_q.where(Product.sale_status == status)

    total = await db.scalar(count_q) or 0
    pages = max(1, (total + size - 1) // size)

    q = q.offset((page - 1) * size).limit(size)
    rows = (await db.scalars(q)).all()

    show_cost = current_staff.role in (StaffRole.사장, StaffRole.총괄)

    return ProductListResponse(
        items=[_to_response(r, show_cost=show_cost) for r in rows],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get("/{product_id}", summary="상품 상세")
async def get_product(
    product_id: int,
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProductDetailResponse:
    product = await db.scalar(select(Product).where(Product.id == product_id))
    if not product:
        raise HTTPException(404, "상품을 찾을 수 없습니다.")

    show_cost = current_staff.role in (StaffRole.사장, StaffRole.총괄)
    base = _to_response(product, show_cost=show_cost)

    resp = ProductDetailResponse(**base.model_dump())
    if show_cost:
        resp.margin_rate = product.margin_rate
    return resp
