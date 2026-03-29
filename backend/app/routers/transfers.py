"""
매장간 재고 이동 (택배/배달) API 라우터
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, extract, or_
from app.database import get_db
from app.models.store_transfer import StoreTransfer, TransferMethod, TransferStatus
from app.models.inventory import Inventory
from app.models.inventory_move import InventoryMove, MoveType
from app.models.product import Product
from app.core.deps import get_current_staff
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date

router = APIRouter()


class TransferRequest(BaseModel):
    from_store_id:   int
    to_store_id:     int
    product_id:      int
    qty:             int
    transfer_method: str
    reason:          str
    memo:            Optional[str] = None


class FeeSettleRequest(BaseModel):
    transfer_ids: list[int]
    month:        str


async def make_transfer_number(db: AsyncSession) -> str:
    today = date.today().strftime("%y%m%d")
    result = await db.execute(
        select(StoreTransfer).where(StoreTransfer.transfer_number.like(f"TF-{today}-%"))
    )
    count = len(result.scalars().all())
    return f"TF-{today}-{str(count + 1).zfill(3)}"


@router.post("")
async def request_transfer(
    body: TransferRequest,
    db: AsyncSession = Depends(get_db),
    staff=Depends(get_current_staff),
):
    if body.qty <= 0:
        raise HTTPException(400, "수량은 1 이상이어야 합니다")
    if not body.reason.strip():
        raise HTTPException(400, "이동 사유를 입력해주세요")
    if body.from_store_id == body.to_store_id:
        raise HTTPException(400, "출발 매장과 도착 매장이 같습니다")

    inv_result = await db.execute(
        select(Inventory).where(
            Inventory.product_id == body.product_id,
            Inventory.store_id == body.from_store_id,
        )
    )
    inv = inv_result.scalar_one_or_none()
    if not inv or inv.qty_available < body.qty:
        raise HTTPException(400, f"출발 매장 가용 재고 부족 (현재 {inv.qty_available if inv else 0}개)")

    prod_result = await db.execute(select(Product).where(Product.id == body.product_id))
    product = prod_result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "상품을 찾을 수 없습니다")

    transfer = StoreTransfer(
        transfer_number=await make_transfer_number(db),
        from_store_id=body.from_store_id,
        to_store_id=body.to_store_id,
        product_id=body.product_id,
        qty=body.qty,
        unit_cost=product.normal_price,
        transfer_method=body.transfer_method,
        reason=body.reason,
        memo=body.memo,
        requested_by=staff.id,
        status=TransferStatus.신청,
    )
    db.add(transfer)
    await db.commit()
    await db.refresh(transfer)
    return {"id": transfer.id, "transfer_number": transfer.transfer_number, "status": transfer.status}


@router.post("/{transfer_id}/ship")
async def ship_transfer(
    transfer_id: int,
    db: AsyncSession = Depends(get_db),
    staff=Depends(get_current_staff),
):
    result = await db.execute(select(StoreTransfer).where(StoreTransfer.id == transfer_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "이동 신청을 찾을 수 없습니다")
    if t.status != TransferStatus.신청:
        raise HTTPException(400, f"발송 처리 불가 (현재 상태: {t.status})")

    inv_result = await db.execute(
        select(Inventory).where(Inventory.product_id == t.product_id, Inventory.store_id == t.from_store_id)
    )
    inv = inv_result.scalar_one_or_none()
    if not inv or inv.qty_actual < t.qty:
        raise HTTPException(400, "출발 매장 재고가 부족합니다")

    before = inv.qty_actual
    inv.qty_actual -= t.qty

    move = InventoryMove(
        product_id=t.product_id, store_id=t.from_store_id,
        move_type=MoveType.택배배달출고, qty=-t.qty,
        qty_before=before, qty_after=inv.qty_actual,
        target_store_id=t.to_store_id, processed_by=staff.id,
        memo=f"[{t.transfer_number}] 발송",
    )
    db.add(move)
    await db.flush()

    t.status = TransferStatus.발송중
    t.shipped_by = staff.id
    t.shipped_at = datetime.now()
    t.ship_move_id = move.id
    await db.commit()
    return {"transfer_number": t.transfer_number, "status": t.status, "from_store_stock_after": inv.qty_actual}


@router.post("/{transfer_id}/receive")
async def receive_transfer(
    transfer_id: int,
    db: AsyncSession = Depends(get_db),
    staff=Depends(get_current_staff),
):
    result = await db.execute(select(StoreTransfer).where(StoreTransfer.id == transfer_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "이동 신청을 찾을 수 없습니다")
    if t.status != TransferStatus.발송중:
        raise HTTPException(400, f"수령 처리 불가 (현재 상태: {t.status})")

    inv_result = await db.execute(
        select(Inventory).where(Inventory.product_id == t.product_id, Inventory.store_id == t.to_store_id)
    )
    inv = inv_result.scalar_one_or_none()
    if not inv:
        inv = Inventory(product_id=t.product_id, store_id=t.to_store_id, qty_actual=0)
        db.add(inv)
        await db.flush()

    before = inv.qty_actual
    inv.qty_actual += t.qty

    move = InventoryMove(
        product_id=t.product_id, store_id=t.to_store_id,
        move_type=MoveType.택배배달입고, qty=t.qty,
        qty_before=before, qty_after=inv.qty_actual,
        target_store_id=t.from_store_id, processed_by=staff.id,
        memo=f"[{t.transfer_number}] 수령",
    )
    db.add(move)
    await db.flush()

    t.status = TransferStatus.수령완료
    t.received_by = staff.id
    t.received_at = datetime.now()
    t.receive_move_id = move.id
    await db.commit()
    return {"transfer_number": t.transfer_number, "status": t.status, "to_store_stock_after": inv.qty_actual, "total_cost": t.total_cost}


@router.post("/{transfer_id}/cancel")
async def cancel_transfer(
    transfer_id: int,
    cancel_reason: str,
    db: AsyncSession = Depends(get_db),
    staff=Depends(get_current_staff),
):
    result = await db.execute(select(StoreTransfer).where(StoreTransfer.id == transfer_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "이동 신청을 찾을 수 없습니다")
    if t.status != TransferStatus.신청:
        raise HTTPException(400, "발송 전(신청 상태)에만 취소 가능합니다")
    t.status = TransferStatus.취소
    t.cancelled_by = staff.id
    t.cancelled_at = datetime.now()
    t.cancel_reason = cancel_reason
    await db.commit()
    return {"transfer_number": t.transfer_number, "status": t.status}


@router.get("")
async def get_transfers(
    store_id: int = Query(...),
    status: Optional[str] = Query(None),
    month: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    staff=Depends(get_current_staff),
):
    q = select(StoreTransfer).where(
        or_(StoreTransfer.from_store_id == store_id, StoreTransfer.to_store_id == store_id)
    )
    if status:
        q = q.where(StoreTransfer.status == status)
    if month:
        y, m = month.split("-")
        q = q.where(
            extract('year', StoreTransfer.requested_at) == int(y),
            extract('month', StoreTransfer.requested_at) == int(m),
        )
    result = await db.execute(q.order_by(StoreTransfer.requested_at.desc()))
    transfers = result.scalars().all()
    return [
        {
            "id": t.id, "transfer_number": t.transfer_number,
            "from_store_id": t.from_store_id, "to_store_id": t.to_store_id,
            "product_id": t.product_id, "qty": t.qty,
            "transfer_method": t.transfer_method, "reason": t.reason,
            "status": t.status, "total_cost": t.total_cost,
            "fee_settled": t.fee_settled, "requested_at": t.requested_at,
            "shipped_at": t.shipped_at, "received_at": t.received_at,
        }
        for t in transfers
    ]


@router.get("/fee-summary")
async def fee_summary(
    month: str = Query(...),
    from_store_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    staff=Depends(get_current_staff),
):
    y, m = month.split("-")
    q = select(StoreTransfer).where(
        StoreTransfer.transfer_method == TransferMethod.택배,
        StoreTransfer.status == TransferStatus.수령완료,
        StoreTransfer.fee_settled == False,
        extract('year', StoreTransfer.received_at) == int(y),
        extract('month', StoreTransfer.received_at) == int(m),
    )
    if from_store_id:
        q = q.where(StoreTransfer.from_store_id == from_store_id)
    result = await db.execute(q)
    transfers = result.scalars().all()
    return {
        "month": month,
        "total_count": len(transfers),
        "total_amount": sum(t.total_cost for t in transfers),
        "transfers": [{"id": t.id, "transfer_number": t.transfer_number, "to_store_id": t.to_store_id, "qty": t.qty, "unit_cost": t.unit_cost, "delivery_fee": t.delivery_fee, "total_cost": t.total_cost} for t in transfers],
    }


@router.post("/fee-settle")
async def settle_fees(
    body: FeeSettleRequest,
    db: AsyncSession = Depends(get_db),
    staff=Depends(get_current_staff),
):
    if not staff.can_transfer_inventory:
        raise HTTPException(403, "총괄 또는 사장만 정산 처리할 수 있습니다")
    result = await db.execute(select(StoreTransfer).where(StoreTransfer.id.in_(body.transfer_ids)))
    transfers = result.scalars().all()
    for t in transfers:
        t.fee_settled = True
        t.fee_settled_month = body.month
    await db.commit()
    return {"settled_count": len(transfers), "month": body.month}
