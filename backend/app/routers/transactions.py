"""
routers/transactions.py — 거래 API

GET  /transactions/        거래 목록
GET  /transactions/{id}    거래 상세
POST /transactions/        거래 생성 (판매 저장)
"""

from typing import Annotated, Optional, List
from datetime import datetime, timezone, date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_staff
from app.database import get_db
from app.models.transaction import Transaction, TxChannel, TxStatus, TxColor, PaymentNature
from app.models.transaction_line import TransactionLine
from app.models.payment import Payment, PaymentMethod
from app.models.mileage_ledger import MileageLedger, MileageType
from app.models.service_record import ServiceRecord
from app.models.unpaid_service import UnpaidService
from app.models.inventory_move import InventoryMove, MoveType
from app.models.inventory import Inventory
from app.models.customer import Customer
from app.models.product import Product, LIQUID_ALL, DEVICE_ALL
from app.models.staff import Staff
from app.engines.price_engine import (
    calc_cart, calc_mileage_earn,
    determine_payment_nature, determine_earn_eligible, determine_service_eligible,
)
from app.engines.service_engine import calc_services

router = APIRouter(prefix="/transactions", tags=["거래"])


# ── 응답 스키마 ──────────────────────────────────────────────

class TxLineResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: int
    line_total: int
    is_service: bool

    class Config:
        from_attributes = True


class TxResponse(BaseModel):
    id: int
    tx_number: str
    channel: str
    status: str
    tx_color: str
    customer_id: Optional[int] = None
    staff_id: int
    store_id: int
    subtotal: int
    discount_amount: int
    total_amount: int
    mileage_used: int
    mileage_earned: int
    payment_nature: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TxDetailResponse(TxResponse):
    lines: List[TxLineResponse] = []
    discount_reason: Optional[str] = None
    staff_memo: Optional[str] = None
    adult_verified: bool = False


# ── 요청 스키마 ──────────────────────────────────────────────

class TxLineRequest(BaseModel):
    product_id: int
    quantity: int = 1
    is_service: bool = False
    service_reason: Optional[str] = None


class PaymentRequest(BaseModel):
    method: PaymentMethod
    amount: int


class ServiceItemRequest(BaseModel):
    service_type: str
    quantity: int = 1
    product_id: Optional[int] = None
    note: Optional[str] = None
    is_unpaid: bool = False


class TxCreateRequest(BaseModel):
    channel: TxChannel
    customer_id: Optional[int] = None
    store_id: int
    lines: List[TxLineRequest]
    payments: List[PaymentRequest] = []
    discount_amount: int = 0
    discount_reason: Optional[str] = None
    mileage_used: int = 0
    card_ratio_pct: int = 0
    adult_verified: bool = False
    staff_memo: Optional[str] = None
    services: List[ServiceItemRequest] = []


# ── 거래번호 생성 ────────────────────────────────────────────

async def _generate_tx_number(db: AsyncSession, store_id: int) -> str:
    today = date.today()
    prefix = today.strftime("%y%m%d")
    count = await db.scalar(
        select(sa_func.count(Transaction.id)).where(
            Transaction.tx_number.like(f"{prefix}-%"),
            Transaction.store_id == store_id,
        )
    )
    seq = (count or 0) + 1
    return f"{prefix}-{seq:03d}"


# ── 엔드포인트 ───────────────────────────────────────────────

@router.get("/", summary="거래 목록")
async def list_transactions(
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    db: Annotated[AsyncSession, Depends(get_db)],
    store_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    limit: int = Query(50, le=200),
) -> List[TxResponse]:
    q = select(Transaction).order_by(Transaction.created_at.desc()).limit(limit)

    if store_id:
        if not current_staff.can_access_store(store_id):
            raise HTTPException(403, "해당 매장에 접근 권한이 없습니다.")
        q = q.where(Transaction.store_id == store_id)
    elif not current_staff.can_access_all:
        accessible = current_staff.accessible_store_ids([])
        if accessible:
            q = q.where(Transaction.store_id.in_(accessible))

    if date_from:
        q = q.where(sa_func.date(Transaction.created_at) >= date_from)
    if date_to:
        q = q.where(sa_func.date(Transaction.created_at) <= date_to)

    rows = (await db.scalars(q)).all()
    return [TxResponse.model_validate(r) for r in rows]


@router.get("/{transaction_id}", summary="거래 상세")
async def get_transaction(
    transaction_id: int,
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TxDetailResponse:
    tx = await db.scalar(
        select(Transaction)
        .where(Transaction.id == transaction_id)
        .options(selectinload(Transaction.lines))
    )
    if not tx:
        raise HTTPException(404, "거래를 찾을 수 없습니다.")
    if not current_staff.can_access_store(tx.store_id):
        raise HTTPException(403, "해당 매장에 접근 권한이 없습니다.")

    resp = TxDetailResponse.model_validate(tx)
    resp.lines = [TxLineResponse.model_validate(l) for l in tx.lines]
    return resp


@router.post("/", status_code=201, summary="거래 생성")
async def create_transaction(
    body: TxCreateRequest,
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    # ── 권한 체크 ─────────────────────────────────────────
    if not current_staff.can_access_store(body.store_id):
        raise HTTPException(403, "해당 매장에 접근 권한이 없습니다.")

    if body.discount_amount > 0 and not body.discount_reason:
        raise HTTPException(400, "할인 사유는 필수입니다.")

    if not body.lines:
        raise HTTPException(400, "상품이 비어있습니다.")

    # ── 상품 조회 및 가격 계산 (price_engine) ──────────────
    products_with_qty = []
    product_map = {}
    for line_req in body.lines:
        product = await db.scalar(select(Product).where(Product.id == line_req.product_id))
        if not product:
            raise HTTPException(400, f"상품 ID {line_req.product_id}를 찾을 수 없습니다.")
        product_map[line_req.product_id] = product
        if not line_req.is_service:
            products_with_qty.append((product, line_req.quantity))

    cart = calc_cart(products_with_qty)

    # ── 결제 성격 판별 ────────────────────────────────────
    card_amount = sum(p.amount for p in body.payments if p.method == PaymentMethod.카드)
    subtotal = cart.subtotal
    total_amount = subtotal - body.discount_amount - body.mileage_used
    if total_amount < 0:
        total_amount = 0

    payment_nature_str = determine_payment_nature(total_amount, card_amount, body.mileage_used)
    earn_eligible = determine_earn_eligible(payment_nature_str, cart.has_high_pod)
    service_eligible = determine_service_eligible(payment_nature_str)

    # ── 적립금 계산 ───────────────────────────────────────
    mileage_earned = calc_mileage_earn(total_amount, eligible=earn_eligible)

    # ── 고객 마일리지 차감 검증 ───────────────────────────
    customer = None
    if body.customer_id:
        customer = await db.scalar(select(Customer).where(Customer.id == body.customer_id))
        if not customer:
            raise HTTPException(400, "고객을 찾을 수 없습니다.")
    if body.mileage_used > 0:
        if not customer:
            raise HTTPException(400, "마일리지 사용 시 고객 정보가 필요합니다.")
        if customer.mileage_balance < body.mileage_used:
            raise HTTPException(400, "적립금 잔액이 부족합니다.")

    # ── 색상 태그 결정 ────────────────────────────────────
    tx_color = TxColor.정상
    if body.discount_amount > 0:
        tx_color = TxColor.할인
    if cart.has_high_pod:
        tx_color = TxColor.고가팟
    if payment_nature_str == "마일리지전액":
        tx_color = TxColor.마일리지전액

    # ── 거래 생성 ─────────────────────────────────────────
    tx_number = await _generate_tx_number(db, body.store_id)

    tx = Transaction(
        tx_number=tx_number,
        channel=body.channel,
        status=TxStatus.완료,
        tx_color=tx_color,
        customer_id=body.customer_id,
        staff_id=current_staff.id,
        store_id=body.store_id,
        subtotal=subtotal,
        discount_amount=body.discount_amount,
        discount_reason=body.discount_reason,
        total_amount=total_amount,
        mileage_used=body.mileage_used,
        mileage_earned=mileage_earned,
        payment_nature=payment_nature_str,
        card_ratio_pct=body.card_ratio_pct,
        service_eligible=service_eligible,
        earn_eligible=earn_eligible,
        adult_verified=body.adult_verified,
        staff_memo=body.staff_memo,
    )
    db.add(tx)
    await db.flush()

    # ── TransactionLine 생성 ──────────────────────────────
    # cart.lines에서 가격 정보를 사용하되, 원본 요청의 is_service도 반영
    cart_line_map = {l.product_id: l for l in cart.lines}
    for line_req in body.lines:
        product = product_map[line_req.product_id]
        if line_req.is_service:
            unit_price = 0
            line_total = 0
            is_dd = False
        else:
            cl = cart_line_map.get(line_req.product_id)
            if cl:
                unit_price = cl.unit_price
                line_total = cl.line_total
                is_dd = cl.is_device_discount
            else:
                unit_price = product.normal_price
                line_total = product.normal_price * line_req.quantity
                is_dd = False

        db.add(TransactionLine(
            transaction_id=tx.id,
            product_id=line_req.product_id,
            quantity=line_req.quantity,
            unit_price=unit_price,
            line_total=line_total,
            is_device_discount=is_dd,
            is_service=line_req.is_service,
            service_reason=line_req.service_reason,
        ))

    # ── Payment 생성 ──────────────────────────────────────
    for pay_req in body.payments:
        db.add(Payment(
            transaction_id=tx.id,
            method=pay_req.method,
            amount=pay_req.amount,
        ))

    # ── MileageLedger (사용) ──────────────────────────────
    if body.mileage_used > 0 and customer:
        customer.mileage_balance -= body.mileage_used
        db.add(MileageLedger(
            customer_id=customer.id,
            transaction_id=tx.id,
            mileage_type=MileageType.사용,
            amount=-body.mileage_used,
            balance_after=customer.mileage_balance,
            staff_id=current_staff.id,
        ))

    # ── MileageLedger (적립) ──────────────────────────────
    if mileage_earned > 0 and customer:
        customer.mileage_balance += mileage_earned
        db.add(MileageLedger(
            customer_id=customer.id,
            transaction_id=tx.id,
            mileage_type=MileageType.적립,
            amount=mileage_earned,
            balance_after=customer.mileage_balance,
            staff_id=current_staff.id,
        ))

    # ── 고객 방문 갱신 ────────────────────────────────────
    if customer:
        customer.visit_count += 1
        customer.total_purchase += total_amount
        customer.last_visit_at = datetime.now(timezone.utc)

    # ── ServiceRecord / UnpaidService 생성 ────────────────
    liquid_count = sum(
        q for p, q in products_with_qty if p.category in LIQUID_ALL
    )
    device_count = sum(
        q for p, q in products_with_qty if p.category in DEVICE_ALL
    )
    svc_result = calc_services(liquid_count, device_count, service_eligible=service_eligible)

    for svc_item in svc_result.items:
        db.add(ServiceRecord(
            transaction_id=tx.id,
            service_type=svc_item.service_type,
            quantity=svc_item.quantity,
            note=svc_item.note,
        ))

    # 클라이언트가 지정한 미지급 서비스
    for svc_req in body.services:
        if svc_req.is_unpaid and customer:
            db.add(UnpaidService(
                customer_id=customer.id,
                transaction_id=tx.id,
                service_type=svc_req.service_type,
                quantity=svc_req.quantity,
                note=svc_req.note,
            ))

    # ── InventoryMove (재고 차감) ─────────────────────────
    for line_req in body.lines:
        if line_req.is_service:
            move_type = MoveType.서비스차감
        else:
            move_type = MoveType.판매차감

        product = product_map[line_req.product_id]
        inv = await db.scalar(
            select(Inventory).where(
                Inventory.store_id == body.store_id,
                Inventory.product_id == line_req.product_id,
            )
        )
        qty_before = inv.quantity if inv else 0
        qty_after = qty_before - line_req.quantity

        if inv:
            inv.quantity = qty_after
        else:
            inv = Inventory(
                store_id=body.store_id,
                product_id=line_req.product_id,
                quantity=qty_after,
            )
            db.add(inv)

        db.add(InventoryMove(
            store_id=body.store_id,
            product_id=line_req.product_id,
            transaction_id=tx.id,
            move_type=move_type,
            quantity=-line_req.quantity,
            quantity_before=qty_before,
            quantity_after=qty_after,
            staff_id=current_staff.id,
        ))

    await db.commit()
    return {
        "message": "거래가 생성되었습니다.",
        "transaction_id": tx.id,
        "tx_number": tx_number,
        "subtotal": subtotal,
        "total_amount": total_amount,
        "mileage_earned": mileage_earned,
        "payment_nature": payment_nature_str,
        "service_eligible": service_eligible,
        "earn_eligible": earn_eligible,
    }
