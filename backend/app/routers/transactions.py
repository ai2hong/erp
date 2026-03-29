"""
거래 API 라우터
POST /transactions      — 거래 저장
GET  /transactions      — 거래 목록 (날짜 기준)
GET  /transactions/{id} — 거래 단건
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date
from app.database import get_db
from app.models.transaction import Transaction, TxChannel, TxColor, TxStatus, PaymentNature
from app.models.transaction_line import TransactionLine
from app.models.payment import Payment, PaymentMethod
from app.models.customer import Customer
from app.models.mileage_ledger import MileageLedger, MileageType
from app.models.service_record import ServiceRecord
from app.models.inventory import Inventory
from app.models.inventory_move import InventoryMove, MoveType
from app.core.deps import get_current_staff
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
import math

router = APIRouter()


class TxLineIn(BaseModel):
    product_id:         int
    quantity:           int
    unit_price:         int
    line_total:         int
    is_device_discount: bool = False
    is_service:         bool = False
    service_reason:     Optional[str] = None


class PaymentIn(BaseModel):
    method: str
    amount: int


class ServiceIn(BaseModel):
    service_type:   str
    product_id:     Optional[int] = None
    quantity:       int = 1
    estimated_cost: int = 0
    note:           Optional[str] = None


class TransactionCreate(BaseModel):
    store_id:        int
    channel:         str
    customer_id:     Optional[int] = None
    subtotal:        int
    discount_amount: int = 0
    discount_reason: Optional[str] = None
    total_amount:    int
    mileage_used:    int = 0
    mileage_earned:  int = 0
    payment_nature:  str
    card_ratio_pct:  int = 0
    service_eligible: bool = True
    earn_eligible:   bool = False
    tx_color:        str = "정상"
    lines:    List[TxLineIn]  = []
    payments: List[PaymentIn] = []
    services: List[ServiceIn] = []


async def _make_tx_number(db: AsyncSession) -> str:
    today = date.today().strftime("%y%m%d")
    result = await db.execute(
        select(func.count()).where(
            Transaction.tx_number.like(f"{today}-%")
        )
    )
    count = result.scalar() or 0
    return f"{today}-{str(count + 1).zfill(3)}"


@router.post("")
async def create_transaction(
    body: TransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    tx = Transaction(
        tx_number       = await _make_tx_number(db),
        store_id        = body.store_id,
        staff_id        = current_staff.id,
        customer_id     = body.customer_id,
        channel         = body.channel,
        subtotal        = body.subtotal,
        discount_amount = body.discount_amount,
        discount_reason = body.discount_reason,
        total_amount    = body.total_amount,
        mileage_used    = body.mileage_used,
        mileage_earned  = body.mileage_earned,
        payment_nature  = body.payment_nature,
        card_ratio_pct  = body.card_ratio_pct,
        service_eligible = body.service_eligible,
        earn_eligible   = body.earn_eligible,
        tx_color        = body.tx_color,
        status          = TxStatus.완료,
    )
    db.add(tx)
    await db.flush()

    for line in body.lines:
        tl = TransactionLine(
            transaction_id     = tx.id,
            product_id         = line.product_id,
            quantity           = line.quantity,
            unit_price         = line.unit_price,
            line_total         = line.line_total,
            is_device_discount = line.is_device_discount,
            is_service         = line.is_service,
            service_reason     = line.service_reason,
        )
        db.add(tl)

        if not line.is_service:
            inv_result = await db.execute(
                select(Inventory).where(
                    Inventory.product_id == line.product_id,
                    Inventory.store_id   == body.store_id,
                )
            )
            inv = inv_result.scalar_one_or_none()
            if inv:
                before = inv.quantity
                inv.quantity = max(0, inv.quantity - line.quantity)
                db.add(InventoryMove(
                    product_id      = line.product_id,
                    store_id        = body.store_id,
                    transaction_id  = tx.id,
                    move_type       = MoveType.판매출고,
                    quantity        = -line.quantity,
                    quantity_before = before,
                    quantity_after  = inv.quantity,
                    staff_id        = current_staff.id,
                ))

    for pay in body.payments:
        db.add(Payment(transaction_id=tx.id, method=pay.method, amount=pay.amount))

    for svc in body.services:
        db.add(ServiceRecord(
            transaction_id = tx.id,
            product_id     = svc.product_id,
            service_type   = svc.service_type,
            quantity       = svc.quantity,
            estimated_cost = svc.estimated_cost,
            note           = svc.note,
        ))

    if body.customer_id and body.mileage_used > 0:
        cust_result = await db.execute(select(Customer).where(Customer.id == body.customer_id))
        cust = cust_result.scalar_one_or_none()
        if cust:
            cust.mileage_balance -= body.mileage_used
            db.add(MileageLedger(
                customer_id    = body.customer_id,
                transaction_id = tx.id,
                mileage_type   = MileageType.사용,
                amount         = -body.mileage_used,
                balance_after  = cust.mileage_balance,
                processed_by   = current_staff.id,
            ))

    if body.earn_eligible and body.customer_id and body.mileage_earned > 0:
        cust_result = await db.execute(select(Customer).where(Customer.id == body.customer_id))
        cust = cust_result.scalar_one_or_none()
        if cust:
            cust.mileage_balance += body.mileage_earned
            cust.visit_count      = (cust.visit_count or 0) + 1
            cust.last_visit_at    = datetime.now()
            db.add(MileageLedger(
                customer_id    = body.customer_id,
                transaction_id = tx.id,
                mileage_type   = MileageType.적립,
                amount         = body.mileage_earned,
                balance_after  = cust.mileage_balance,
                processed_by   = current_staff.id,
            ))

    await db.commit()
    return {"id": tx.id, "tx_number": tx.tx_number, "message": "거래가 저장됐습니다"}


@router.get("")
async def list_transactions(
    store_id: int = Query(...),
    tx_date:  Optional[str] = Query(None, description="YYYY-MM-DD, 기본 오늘"),
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    target_date = date.fromisoformat(tx_date) if tx_date else date.today()
    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.store_id == store_id,
            cast(Transaction.created_at, Date) == target_date,
        )
        .order_by(Transaction.created_at.desc())
    )
    txs = result.scalars().all()
    return [
        {
            "id":           t.id,
            "tx_number":    t.tx_number,
            "channel":      t.channel,
            "total_amount": t.total_amount,
            "tx_color":     t.tx_color,
            "created_at":   t.created_at,
        }
        for t in txs
    ]


@router.get("/{tx_id}")
async def get_transaction(
    tx_id: int,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    result = await db.execute(select(Transaction).where(Transaction.id == tx_id))
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(404, "거래를 찾을 수 없습니다")
    return tx
