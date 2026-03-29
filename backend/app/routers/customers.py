"""
고객 API 라우터
GET  /customers/search           — 이름·전화번호(두 번호) 검색
GET  /customers/{id}             — 고객 상세
POST /customers                  — 신규 등록
PUT  /customers/{id}             — 정보 수정 (전화번호·주소·메모)
GET  /customers/{id}/mileage     — 적립금 이력
GET  /customers/{id}/transactions — 전체 구매 이력
GET  /customers/{id}/devices     — 기기 구매 이력
GET  /customers/{id}/as-cases    — A/S 내역
GET  /customers/{id}/unpaid      — 미지급 서비스
GET  /customers/{id}/reservations — 예약 주문
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload, joinedload
from app.database import get_db
from app.models.customer import Customer
from app.models.mileage_ledger import MileageLedger
from app.models.transaction import Transaction
from app.models.transaction_line import TransactionLine
from app.models.product import Product, DEVICE_ALL
from app.models.as_case import AsCase
from app.models.unpaid_service import UnpaidService
from app.models.reservation import Reservation
from app.core.deps import get_current_staff
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


def _customer_dict(c: Customer) -> dict:
    return {
        "id":              c.id,
        "name":            c.name,
        "phone":           c.phone,
        "phone2":          c.phone2,
        "default_phone":   c.default_phone,
        "mileage_balance": c.mileage_balance,
        "visit_count":     c.visit_count,
        "total_purchase":  c.total_purchase,
        "last_visit_at":   c.last_visit_at,
        "staff_memo":      c.staff_memo,
        "address":         c.address,
        "address2":        c.address2,
        "default_address": c.default_address,
        "created_at":      c.created_at,
    }


class CustomerCreate(BaseModel):
    name:       str
    phone:      str
    phone2:     Optional[str] = None
    staff_memo: Optional[str] = None
    address:    Optional[str] = None
    address2:   Optional[str] = None


class CustomerUpdate(BaseModel):
    phone:           Optional[str] = None
    phone2:          Optional[str] = None
    default_phone:   Optional[int] = None   # 1 or 2
    staff_memo:      Optional[str] = None
    address:         Optional[str] = None
    address2:        Optional[str] = None
    default_address: Optional[int] = None   # 1 or 2


# ── 전체 목록 (최신순) ────────────────────────────────────────
@router.get("")
async def list_customers(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    result = await db.execute(
        select(Customer)
        .where(Customer.is_deleted == False)
        .order_by(Customer.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [_customer_dict(c) for c in result.scalars().all()]


# ── 검색 ─────────────────────────────────────────────────────
@router.get("/search")
async def search_customer(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    result = await db.execute(
        select(Customer).where(
            Customer.is_deleted == False,
            or_(
                Customer.name.contains(q),
                Customer.phone.contains(q),
                Customer.phone2.contains(q),
            )
        ).order_by(Customer.name).limit(30)
    )
    return [_customer_dict(c) for c in result.scalars().all()]


# ── 단건 조회 ─────────────────────────────────────────────────
@router.get("/{customer_id}")
async def get_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    c = await db.scalar(
        select(Customer).where(Customer.id == customer_id, Customer.is_deleted == False)
    )
    if not c:
        raise HTTPException(404, "고객을 찾을 수 없습니다")
    return _customer_dict(c)


# ── 신규 등록 ─────────────────────────────────────────────────
@router.post("")
async def create_customer(
    body: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    if await db.scalar(select(Customer).where(Customer.phone == body.phone, Customer.is_deleted == False)):
        raise HTTPException(409, "이미 등록된 전화번호입니다")
    c = Customer(
        name=body.name, phone=body.phone, phone2=body.phone2,
        staff_memo=body.staff_memo, address=body.address, address2=body.address2,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return _customer_dict(c)


# ── 정보 수정 ─────────────────────────────────────────────────
@router.put("/{customer_id}")
async def update_customer(
    customer_id: int,
    body: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    c = await db.scalar(
        select(Customer).where(Customer.id == customer_id, Customer.is_deleted == False)
    )
    if not c:
        raise HTTPException(404, "고객을 찾을 수 없습니다")

    if body.phone is not None:
        # 다른 고객이 같은 번호 쓰는지 확인
        dup = await db.scalar(
            select(Customer).where(
                Customer.phone == body.phone,
                Customer.id != customer_id,
                Customer.is_deleted == False,
            )
        )
        if dup:
            raise HTTPException(409, "이미 사용 중인 전화번호입니다")
        c.phone = body.phone
    if body.phone2          is not None: c.phone2          = body.phone2 or None
    if body.default_phone   is not None: c.default_phone   = body.default_phone
    if body.staff_memo      is not None: c.staff_memo      = body.staff_memo or None
    if body.address         is not None: c.address         = body.address or None
    if body.address2        is not None: c.address2        = body.address2 or None
    if body.default_address is not None: c.default_address = body.default_address

    await db.commit()
    await db.refresh(c)
    return _customer_dict(c)


# ── 적립금 이력 ───────────────────────────────────────────────
@router.get("/{customer_id}/mileage")
async def get_mileage(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    result = await db.execute(
        select(MileageLedger)
        .where(MileageLedger.customer_id == customer_id)
        .order_by(MileageLedger.created_at.desc())
        .limit(100)
    )
    rows = result.scalars().all()
    return [
        {
            "id":            r.id,
            "mileage_type":  r.mileage_type,
            "amount":        r.amount,
            "balance_after": r.balance_after,
            "note":          r.note,
            "transaction_id": r.transaction_id,
            "created_at":    r.created_at,
        }
        for r in rows
    ]


# ── 전체 구매 이력 ────────────────────────────────────────────
@router.get("/{customer_id}/transactions")
async def get_tx_history(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    result = await db.execute(
        select(Transaction)
        .where(Transaction.customer_id == customer_id)
        .options(selectinload(Transaction.lines).joinedload(TransactionLine.product))
        .order_by(Transaction.created_at.desc())
        .limit(200)
    )
    txs = result.scalars().all()

    def _summary(tx):
        normal = [l for l in tx.lines if not l.is_service]
        svc_cnt = sum(1 for l in tx.lines if l.is_service)
        parts = []
        for l in normal[:3]:
            name = l.product.name if l.product else f"상품#{l.product_id}"
            parts.append(f"{name} {l.quantity}개" if l.quantity > 1 else name)
        if len(normal) > 3:
            parts.append(f"외 {len(normal)-3}종")
        if svc_cnt:
            parts.append(f"서비스 {svc_cnt}건")
        return " + ".join(parts)

    return [
        {
            "id":             t.id,
            "tx_number":      t.tx_number,
            "channel":        t.channel,
            "total_amount":   t.total_amount,
            "tx_color":       t.tx_color,
            "payment_nature": t.payment_nature,
            "mileage_earned": t.mileage_earned,
            "mileage_used":   t.mileage_used,
            "created_at":     t.created_at,
            "summary":        _summary(t),
        }
        for t in txs
    ]


# ── 기기 구매 이력 ────────────────────────────────────────────
@router.get("/{customer_id}/devices")
async def get_device_history(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    device_categories = [cat.value for cat in DEVICE_ALL]
    result = await db.execute(
        select(TransactionLine, Transaction, Product)
        .join(Transaction, TransactionLine.transaction_id == Transaction.id)
        .join(Product, TransactionLine.product_id == Product.id)
        .where(
            Transaction.customer_id == customer_id,
            Product.category.in_(device_categories),
        )
        .order_by(Transaction.created_at.desc())
    )
    rows = result.all()
    return [
        {
            "transaction_id": tx.id,
            "tx_number":      tx.tx_number,
            "product_id":     prod.id,
            "product_name":   prod.name,
            "category":       prod.category,
            "quantity":       line.quantity,
            "unit_price":     line.unit_price,
            "created_at":     tx.created_at,
        }
        for line, tx, prod in rows
    ]


# ── A/S 내역 ──────────────────────────────────────────────────
@router.get("/{customer_id}/as-cases")
async def get_as_cases(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    result = await db.execute(
        select(AsCase)
        .where(AsCase.customer_id == customer_id)
        .order_by(AsCase.created_at.desc())
    )
    rows = result.scalars().all()
    return [
        {
            "id":          r.id,
            "product_id":  r.product_id,
            "symptom":     r.symptom,
            "diagnosis":   r.diagnosis,
            "resolution":  r.resolution,
            "status":      r.status,
            "created_at":  r.created_at,
        }
        for r in rows
    ]


# ── 미지급 서비스 ─────────────────────────────────────────────
@router.get("/{customer_id}/unpaid")
async def get_unpaid(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    result = await db.execute(
        select(UnpaidService)
        .where(UnpaidService.customer_id == customer_id)
        .order_by(UnpaidService.created_at.desc())
    )
    rows = result.scalars().all()
    return [
        {
            "id":            r.id,
            "transaction_id": r.transaction_id,
            "service_type":  r.service_type,
            "quantity":      r.quantity,
            "is_fulfilled":  r.is_fulfilled,
            "note":          r.note,
            "created_at":    r.created_at,
        }
        for r in rows
    ]


# ── 예약 주문 ─────────────────────────────────────────────────
@router.get("/{customer_id}/reservations")
async def get_reservations(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    result = await db.execute(
        select(Reservation)
        .where(Reservation.customer_id == customer_id)
        .order_by(Reservation.created_at.desc())
    )
    rows = result.scalars().all()
    return [
        {
            "id":         r.id,
            "product_id": r.product_id,
            "quantity":   r.quantity,
            "status":     r.status,
            "note":       r.note,
            "created_at": r.created_at,
        }
        for r in rows
    ]
