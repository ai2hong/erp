"""
A/S 관리 API
GET  /as-cases          — 전체 목록 (상태·검색 필터)
POST /as-cases          — 신규 접수
PUT  /as-cases/{id}     — 상태/진단/처리 수정
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.as_case import AsCase, AsStatus
from app.models.customer import Customer
from app.models.product import Product
from app.models.staff import Staff
from app.core.deps import get_current_staff
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


def _as_dict(a: AsCase, customer: Customer = None, product: Product = None, staff: Staff = None) -> dict:
    return {
        "id":              a.id,
        "customer_id":     a.customer_id,
        "customer_name":   customer.name  if customer else None,
        "customer_phone":  customer.phone if customer else None,
        "product_id":      a.product_id,
        "product_name":    product.name   if product  else None,
        "serial_number":   a.serial_number,
        "symptom":         a.symptom,
        "diagnosis":       a.diagnosis,
        "resolution":      a.resolution,
        "status":          a.status,
        "received_by":     a.received_by,
        "received_by_name": staff.name   if staff    else None,
        "created_at":      a.created_at,
        "updated_at":      a.updated_at,
    }


class AsCaseCreate(BaseModel):
    customer_id:   int
    product_id:    Optional[int] = None
    serial_number: Optional[str] = None   # 검색 불가 시 기기명 직접 입력
    symptom:       Optional[str] = None


class AsCaseUpdate(BaseModel):
    status:     Optional[str] = None
    diagnosis:  Optional[str] = None
    resolution: Optional[str] = None
    symptom:    Optional[str] = None


# ── 전체 목록 ──────────────────────────────────────────────────
@router.get("")
async def list_as_cases(
    status: Optional[str] = Query(None),
    q:      Optional[str] = Query(None, description="고객명 검색"),
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    stmt = (
        select(AsCase, Customer, Product, Staff)
        .join(Customer, AsCase.customer_id == Customer.id)
        .outerjoin(Product, AsCase.product_id == Product.id)
        .outerjoin(Staff, AsCase.received_by == Staff.id)
        .order_by(AsCase.created_at.desc())
        .limit(200)
    )
    if status:
        stmt = stmt.where(AsCase.status == status)
    if q:
        stmt = stmt.where(Customer.name.contains(q) | Customer.phone.contains(q))

    result = await db.execute(stmt)
    rows = result.all()
    return [_as_dict(a, c, p, s) for a, c, p, s in rows]


# ── 신규 접수 ──────────────────────────────────────────────────
@router.post("")
async def create_as_case(
    body: AsCaseCreate,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    c = await db.scalar(select(Customer).where(Customer.id == body.customer_id, Customer.is_deleted == False))
    if not c:
        raise HTTPException(404, "고객을 찾을 수 없습니다")

    try:
        a = AsCase(
            customer_id=body.customer_id,
            product_id=body.product_id,
            serial_number=body.serial_number,
            symptom=body.symptom or "",
            status=AsStatus.접수,
            received_by=current_staff.id,
            store_id=current_staff.store_id,
        )
        db.add(a)
        await db.commit()
        await db.refresh(a)
    except Exception as e:
        import traceback
        await db.rollback()
        traceback.print_exc()
        raise HTTPException(500, f"DB 저장 실패: {type(e).__name__}: {str(e)}")

    prod = await db.scalar(select(Product).where(Product.id == a.product_id)) if a.product_id else None
    return _as_dict(a, c, prod, current_staff)


# ── 수정 ───────────────────────────────────────────────────────
@router.put("/{case_id}")
async def update_as_case(
    case_id: int,
    body: AsCaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    a = await db.scalar(select(AsCase).where(AsCase.id == case_id))
    if not a:
        raise HTTPException(404, "A/S 건을 찾을 수 없습니다")

    if body.status     is not None: a.status     = AsStatus(body.status)
    if body.diagnosis  is not None: a.diagnosis  = body.diagnosis or None
    if body.resolution is not None: a.resolution = body.resolution or None
    if body.symptom    is not None: a.symptom    = body.symptom or ""

    try:
        await db.commit()
        await db.refresh(a)
    except Exception as e:
        import traceback
        await db.rollback()
        traceback.print_exc()
        raise HTTPException(500, f"DB 저장 실패: {type(e).__name__}: {str(e)}")

    c     = await db.scalar(select(Customer).where(Customer.id == a.customer_id))
    prod  = await db.scalar(select(Product).where(Product.id == a.product_id)) if a.product_id else None
    staff = await db.scalar(select(Staff).where(Staff.id == a.received_by))    if a.received_by else None
    return _as_dict(a, c, prod, staff)
