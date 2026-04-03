"""
A/S 관리 API
GET  /as-cases              — 전체 목록 (상태·검색 필터)
GET  /as-cases/{id}         — 단건 + 이력 로그
POST /as-cases              — 신규 접수
PUT  /as-cases/{id}         — 증상·진단·처리·판정 수정
POST /as-cases/{id}/next    — 다음 상태로 진행
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.as_case import AsCase, AsStatus
from app.models.as_case_log import AsCaseLog
from app.models.customer import Customer
from app.models.product import Product
from app.models.staff import Staff
from app.models.approval_log import ApprovalLog, ExceptionType, ApprovalStatus
from app.core.deps import get_current_staff
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

STATUS_ORDER = ["접수", "발송/처리중", "입고", "연락완료", "AS완료"]


def _next_status(current: str) -> Optional[str]:
    try:
        idx = STATUS_ORDER.index(current)
        return STATUS_ORDER[idx + 1] if idx + 1 < len(STATUS_ORDER) else None
    except ValueError:
        return None


def _as_dict(a: AsCase, customer: Customer = None, product: Product = None, staff: Staff = None) -> dict:
    return {
        "id":                a.id,
        "customer_id":       a.customer_id,
        "customer_name":     customer.name  if customer else None,
        "customer_phone":    customer.phone if customer else None,
        "product_id":        a.product_id,
        "product_name":      product.name   if product  else None,
        "serial_number":     a.serial_number,
        "symptom":           a.symptom,
        "diagnosis":         a.diagnosis,
        "resolution":        a.resolution,
        "status":            a.status,
        "wholesale_verdict": a.wholesale_verdict,
        "repair_cost":       a.repair_cost,
        "received_by":       a.received_by,
        "received_by_name":  staff.name     if staff    else None,
        "loaner_note":       a.loaner_note,
        "loaner_out_date":   a.loaner_out_date,
        "loaner_return_date": a.loaner_return_date,
        "created_at":        a.created_at,
        "updated_at":        a.updated_at,
        "next_status":       _next_status(a.status),
    }


class AsCaseCreate(BaseModel):
    customer_id:   int
    product_id:    Optional[int] = None
    serial_number: Optional[str] = None
    symptom:       Optional[str] = None
    loaner_note:   Optional[str] = None


class AsCaseUpdate(BaseModel):
    symptom:           Optional[str] = None
    diagnosis:         Optional[str] = None
    resolution:        Optional[str] = None
    wholesale_verdict: Optional[str] = None
    repair_cost:       Optional[int] = None


class NextStatusBody(BaseModel):
    memo: Optional[str] = None


class SetStatusBody(BaseModel):
    to_status: str
    memo:      Optional[str] = None


# ── 전체 목록 ──────────────────────────────────────────────────
@router.get("")
async def list_as_cases(
    status: Optional[str] = Query(None),
    q:      Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    stmt = (
        select(AsCase, Customer, Product, Staff)
        .join(Customer, AsCase.customer_id == Customer.id)
        .outerjoin(Product, AsCase.product_id == Product.id)
        .outerjoin(Staff, AsCase.received_by == Staff.id)
        .order_by(AsCase.created_at.desc())
        .limit(300)
    )
    if status:
        stmt = stmt.where(AsCase.status == status)
    if q:
        stmt = stmt.where(Customer.name.contains(q) | Customer.phone.contains(q))

    result = await db.execute(stmt)
    return [_as_dict(a, c, p, s) for a, c, p, s in result.all()]


# ── 단건 + 이력 ────────────────────────────────────────────────
@router.get("/{case_id}")
async def get_as_case(
    case_id: int,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    row = await db.execute(
        select(AsCase, Customer, Product, Staff)
        .join(Customer, AsCase.customer_id == Customer.id)
        .outerjoin(Product, AsCase.product_id == Product.id)
        .outerjoin(Staff, AsCase.received_by == Staff.id)
        .where(AsCase.id == case_id)
    )
    r = row.first()
    if not r:
        raise HTTPException(404, "A/S 건을 찾을 수 없습니다")
    a, c, p, s = r

    # 이력 로그
    log_rows = await db.execute(
        select(AsCaseLog, Staff)
        .outerjoin(Staff, AsCaseLog.staff_id == Staff.id)
        .where(AsCaseLog.as_case_id == case_id)
        .order_by(AsCaseLog.created_at.asc())
    )
    logs = [
        {
            "id":          lg.id,
            "from_status": lg.from_status,
            "to_status":   lg.to_status,
            "staff_name":  st.name if st else None,
            "memo":        lg.memo,
            "created_at":  lg.created_at,
        }
        for lg, st in log_rows.all()
    ]

    result = _as_dict(a, c, p, s)
    result["logs"] = logs
    return result


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
        loaner = body.loaner_note.strip() if body.loaner_note else None
        a = AsCase(
            customer_id=body.customer_id,
            product_id=body.product_id,
            serial_number=body.serial_number,
            symptom=body.symptom or "",
            status=AsStatus.접수,
            received_by=current_staff.id,
            store_id=current_staff.store_id,
            loaner_note=loaner,
            loaner_out_date=datetime.now(timezone.utc) if loaner else None,
        )
        db.add(a)
        await db.flush()

        log = AsCaseLog(
            as_case_id=a.id,
            from_status=None,
            to_status="접수",
            staff_id=current_staff.id,
            memo="신규 접수",
        )
        db.add(log)
        await db.commit()
        await db.refresh(a)
    except Exception as e:
        import traceback
        await db.rollback()
        traceback.print_exc()
        raise HTTPException(500, f"DB 저장 실패: {type(e).__name__}: {str(e)}")

    prod = await db.scalar(select(Product).where(Product.id == a.product_id)) if a.product_id else None
    return _as_dict(a, c, prod, current_staff)


# ── 내용 수정 ──────────────────────────────────────────────────
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

    if body.symptom           is not None: a.symptom           = body.symptom
    if body.diagnosis         is not None: a.diagnosis         = body.diagnosis or None
    if body.resolution        is not None: a.resolution        = body.resolution or None
    if body.wholesale_verdict is not None: a.wholesale_verdict = body.wholesale_verdict or None
    if body.repair_cost       is not None: a.repair_cost       = body.repair_cost

    try:
        await db.commit()
        await db.refresh(a)
    except Exception as e:
        await db.rollback()
        raise HTTPException(500, f"DB 저장 실패: {str(e)}")

    c    = await db.scalar(select(Customer).where(Customer.id == a.customer_id))
    prod = await db.scalar(select(Product).where(Product.id == a.product_id)) if a.product_id else None
    s    = await db.scalar(select(Staff).where(Staff.id == a.received_by))    if a.received_by else None
    return _as_dict(a, c, prod, s)


# ── 다음 상태로 진행 ───────────────────────────────────────────
@router.post("/{case_id}/next")
async def advance_status(
    case_id: int,
    body: NextStatusBody,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    a = await db.scalar(select(AsCase).where(AsCase.id == case_id))
    if not a:
        raise HTTPException(404, "A/S 건을 찾을 수 없습니다")

    nxt = _next_status(a.status)
    if not nxt:
        raise HTTPException(400, "이미 최종 상태입니다")

    old_status = a.status
    a.status = AsStatus(nxt)

    log = AsCaseLog(
        as_case_id=case_id,
        from_status=old_status,
        to_status=nxt,
        staff_id=current_staff.id,
        memo=body.memo,
    )
    db.add(log)

    try:
        await db.commit()
        await db.refresh(a)
    except Exception as e:
        await db.rollback()
        raise HTTPException(500, f"DB 저장 실패: {str(e)}")

    c    = await db.scalar(select(Customer).where(Customer.id == a.customer_id))
    prod = await db.scalar(select(Product).where(Product.id == a.product_id)) if a.product_id else None
    s    = await db.scalar(select(Staff).where(Staff.id == a.received_by))    if a.received_by else None

    result = _as_dict(a, c, prod, s)

    # 이력 로그도 함께 반환
    log_rows = await db.execute(
        select(AsCaseLog, Staff)
        .outerjoin(Staff, AsCaseLog.staff_id == Staff.id)
        .where(AsCaseLog.as_case_id == case_id)
        .order_by(AsCaseLog.created_at.asc())
    )
    result["logs"] = [
        {
            "id":          lg.id,
            "from_status": lg.from_status,
            "to_status":   lg.to_status,
            "staff_name":  st.name if st else None,
            "memo":        lg.memo,
            "created_at":  lg.created_at,
        }
        for lg, st in log_rows.all()
    ]
    return result


async def _fetch_with_logs(case_id: int, a: AsCase, db: AsyncSession) -> dict:
    """상세 dict + logs 반환 헬퍼"""
    c    = await db.scalar(select(Customer).where(Customer.id == a.customer_id))
    prod = await db.scalar(select(Product).where(Product.id == a.product_id)) if a.product_id else None
    s    = await db.scalar(select(Staff).where(Staff.id == a.received_by))    if a.received_by else None
    result = _as_dict(a, c, prod, s)
    log_rows = await db.execute(
        select(AsCaseLog, Staff)
        .outerjoin(Staff, AsCaseLog.staff_id == Staff.id)
        .where(AsCaseLog.as_case_id == case_id)
        .order_by(AsCaseLog.created_at.asc())
    )
    result["logs"] = [
        {"id": lg.id, "from_status": lg.from_status, "to_status": lg.to_status,
         "staff_name": st.name if st else None, "memo": lg.memo, "created_at": lg.created_at}
        for lg, st in log_rows.all()
    ]
    return result


# ── 임의 상태로 변경 (전진 / 되돌리기 모두) ──────────────────────
@router.post("/{case_id}/set-status")
async def set_status(
    case_id: int,
    body: SetStatusBody,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    if body.to_status not in STATUS_ORDER:
        raise HTTPException(400, "유효하지 않은 상태값입니다")

    a = await db.scalar(select(AsCase).where(AsCase.id == case_id))
    if not a:
        raise HTTPException(404, "A/S 건을 찾을 수 없습니다")

    old_status = a.status
    if old_status == body.to_status:
        raise HTTPException(400, "이미 해당 상태입니다")

    is_revert = STATUS_ORDER.index(body.to_status) < STATUS_ORDER.index(old_status)
    memo_text = body.memo or None
    if is_revert and memo_text:
        memo_text = f"[취소] {memo_text}"
    elif is_revert:
        memo_text = "[취소]"

    a.status = AsStatus(body.to_status)
    log = AsCaseLog(
        as_case_id=case_id,
        from_status=old_status,
        to_status=body.to_status,
        staff_id=current_staff.id,
        memo=memo_text,
    )
    db.add(log)

    try:
        await db.commit()
        await db.refresh(a)
    except Exception as e:
        await db.rollback()
        raise HTTPException(500, f"DB 저장 실패: {str(e)}")

    return await _fetch_with_logs(case_id, a, db)


# ── 대여 기기 회수 처리 ────────────────────────────────────────
@router.post("/{case_id}/return-loaner")
async def return_loaner(
    case_id: int,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    a = await db.scalar(select(AsCase).where(AsCase.id == case_id))
    if not a:
        raise HTTPException(404, "A/S 건을 찾을 수 없습니다")
    if not a.loaner_note:
        raise HTTPException(400, "대여 기기 정보가 없습니다")
    if a.loaner_return_date:
        raise HTTPException(400, "이미 회수 처리되었습니다")

    a.loaner_return_date = datetime.now(timezone.utc)
    log = AsCaseLog(
        as_case_id=case_id,
        from_status=a.status,
        to_status=a.status,
        staff_id=current_staff.id,
        memo=f"[대여기기 회수] {a.loaner_note}",
    )
    db.add(log)
    try:
        await db.commit()
        await db.refresh(a)
    except Exception as e:
        await db.rollback()
        raise HTTPException(500, f"DB 저장 실패: {str(e)}")

    return await _fetch_with_logs(case_id, a, db)


# ── 대여 기기 회수 취소 ────────────────────────────────────────
@router.post("/{case_id}/cancel-return-loaner")
async def cancel_return_loaner(
    case_id: int,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    a = await db.scalar(select(AsCase).where(AsCase.id == case_id))
    if not a:
        raise HTTPException(404, "A/S 건을 찾을 수 없습니다")
    if not a.loaner_return_date:
        raise HTTPException(400, "회수 처리된 내역이 없습니다")

    a.loaner_return_date = None
    log = AsCaseLog(
        as_case_id=case_id,
        from_status=a.status,
        to_status=a.status,
        staff_id=current_staff.id,
        memo=f"[대여기기 회수 취소] {a.loaner_note}",
    )
    db.add(log)
    try:
        await db.commit()
        await db.refresh(a)
    except Exception as e:
        await db.rollback()
        raise HTTPException(500, f"DB 저장 실패: {str(e)}")

    return await _fetch_with_logs(case_id, a, db)


# ── 대여 기기 미반납 처리 요청 ────────────────────────────────
class UnreturnedBody(BaseModel):
    reason: Optional[str] = None


@router.post("/{case_id}/unreturned-loaner")
async def request_unreturned_loaner(
    case_id: int,
    body: UnreturnedBody,
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    a = await db.scalar(select(AsCase).where(AsCase.id == case_id))
    if not a:
        raise HTTPException(404, "A/S 건을 찾을 수 없습니다")
    if not a.loaner_note:
        raise HTTPException(400, "대여 기기 정보가 없습니다")
    if a.loaner_return_date:
        raise HTTPException(400, "이미 회수 완료된 건입니다")

    # 이미 대기중인 미반납 요청 중복 방지
    existing = await db.scalar(
        select(ApprovalLog).where(
            ApprovalLog.as_case_id == case_id,
            ApprovalLog.exception_type == ExceptionType.대여기기미반납,
            ApprovalLog.status == ApprovalStatus.대기,
        )
    )
    if existing:
        raise HTTPException(409, "이미 미반납 처리 요청이 대기 중입니다")

    from datetime import datetime, timezone as tz_
    ts = datetime.now(tz_.utc).strftime("%Y%m%d%H%M%S")
    c = await db.scalar(select(Customer).where(Customer.id == a.customer_id))

    lg = ApprovalLog(
        log_number       = f"LNR-{ts}-{case_id}",
        exception_type   = ExceptionType.대여기기미반납,
        status           = ApprovalStatus.대기,
        exception_reason = body.reason or "대여 기기 미반납",
        original_value   = {
            "as_case_id":    case_id,
            "loaner_note":   a.loaner_note,
            "customer_name": c.name if c else None,
            "customer_phone": c.phone if c else None,
        },
        requested_by  = current_staff.id,
        customer_id   = a.customer_id,
        as_case_id    = case_id,
    )
    db.add(lg)

    log = AsCaseLog(
        as_case_id=case_id,
        from_status=a.status,
        to_status=a.status,
        staff_id=current_staff.id,
        memo=f"[대여기기 미반납 요청] {a.loaner_note}",
    )
    db.add(log)

    try:
        await db.commit()
        await db.refresh(lg)
    except Exception as e:
        await db.rollback()
        raise HTTPException(500, f"DB 저장 실패: {str(e)}")

    return {"id": lg.id, "log_number": lg.log_number, "status": lg.status}

