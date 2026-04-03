"""
승인 로그 API  (ApprovalLog 기반)
GET  /approvals              — 목록 (타입·상태 필터)
GET  /approvals/pending-count — 대기 건수 (사이드바 뱃지용)
POST /approvals/{id}/approve — 승인 [총괄 이상]
POST /approvals/{id}/reject  — 반려 [총괄 이상]
"""
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_staff, RequireGeneral
from app.database import get_db
from app.models.approval_log import ApprovalLog, ApprovalStatus, ExceptionType
from app.models.as_case import AsCase
from app.models.as_case_log import AsCaseLog
from app.models.customer import Customer
from app.models.staff import Staff
from app.models.unpaid_service import UnpaidService

router = APIRouter()


def _log_dict(lg: ApprovalLog, requester: Staff = None, approver: Staff = None, customer: Customer = None) -> dict:
    return {
        "id":               lg.id,
        "log_number":       lg.log_number,
        "exception_type":   lg.exception_type,
        "status":           lg.status,
        "exception_reason": lg.exception_reason,
        "original_value":   lg.original_value,
        "changed_value":    lg.changed_value,
        "customer_id":      lg.customer_id,
        "customer_name":    customer.name  if customer  else None,
        "customer_phone":   customer.phone if customer  else None,
        "as_case_id":       lg.as_case_id,
        "requested_by":     lg.requested_by,
        "requester_name":   requester.name if requester else None,
        "approved_by":      lg.approved_by,
        "approver_name":    approver.name  if approver  else None,
        "rejected_reason":  lg.rejected_reason,
        "requested_at":     lg.requested_at,
        "approved_at":      lg.approved_at,
    }


async def _fetch_log(lg: ApprovalLog, db: AsyncSession) -> dict:
    requester = await db.scalar(select(Staff).where(Staff.id == lg.requested_by)) if lg.requested_by else None
    approver  = await db.scalar(select(Staff).where(Staff.id == lg.approved_by))  if lg.approved_by  else None
    customer  = await db.scalar(select(Customer).where(Customer.id == lg.customer_id)) if lg.customer_id else None
    return _log_dict(lg, requester, approver, customer)


# ── 목록 ───────────────────────────────────────────────────────
@router.get("")
async def list_approvals(
    exception_type: Optional[str] = Query(None),
    status:         Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    stmt = (
        select(ApprovalLog, Staff, Customer)
        .outerjoin(Staff,    ApprovalLog.requested_by == Staff.id)
        .outerjoin(Customer, ApprovalLog.customer_id  == Customer.id)
        .order_by(ApprovalLog.requested_at.desc())
        .limit(200)
    )
    if exception_type:
        stmt = stmt.where(ApprovalLog.exception_type == exception_type)
    if status:
        stmt = stmt.where(ApprovalLog.status == status)

    result = await db.execute(stmt)
    rows = result.all()

    out = []
    for lg, req, cust in rows:
        approver = await db.scalar(select(Staff).where(Staff.id == lg.approved_by)) if lg.approved_by else None
        out.append(_log_dict(lg, req, approver, cust))
    return out


# ── 대기 건수 (뱃지용) ─────────────────────────────────────────
@router.get("/pending-count")
async def pending_count(
    db: AsyncSession = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    cnt = await db.scalar(
        select(func.count(ApprovalLog.id))
        .where(ApprovalLog.status == ApprovalStatus.대기)
    )
    return {"count": cnt or 0}


# ── 승인 ───────────────────────────────────────────────────────
class RejectBody(BaseModel):
    reason: Optional[str] = None


class ApproveBody(BaseModel):
    # 대여기기미반납 전용: 청구 or 포기
    decision:       Optional[str] = None   # "청구" | "포기"
    payment_method: Optional[str] = None   # "현금" | "이체" | "카드" (청구 시)
    charge_amount:  Optional[int] = None   # 청구 금액 (기본 20000)


@router.post("/{log_id}/approve")
async def approve_log(
    log_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[Staff, RequireGeneral],
    body: ApproveBody = Body(default=ApproveBody()),
):
    lg = await db.scalar(select(ApprovalLog).where(ApprovalLog.id == log_id))
    if not lg:
        raise HTTPException(404, "승인 건을 찾을 수 없습니다")
    if lg.status != ApprovalStatus.대기:
        raise HTTPException(400, "이미 처리된 건입니다")

    lg.status      = ApprovalStatus.승인
    lg.approved_by = current.id
    lg.approved_at = datetime.now(timezone.utc)

    # 회원삭제: 실제 고객 비활성화
    if lg.exception_type == ExceptionType.회원삭제 and lg.customer_id:
        c = await db.scalar(select(Customer).where(Customer.id == lg.customer_id))
        if c:
            c.is_deleted = True

    # 대여기기미반납: 청구 or 포기 처리
    if lg.exception_type == ExceptionType.대여기기미반납 and lg.as_case_id:
        decision = body.decision or "포기"
        loaner_name = (lg.original_value or {}).get("loaner_note", "대여 기기")
        amount = body.charge_amount or 20000

        if decision == "청구" and lg.customer_id:
            # 미수령 서비스 생성
            unpaid = UnpaidService(
                customer_id  = lg.customer_id,
                service_type = f"대여기기 미반납 청구 ({loaner_name})",
                quantity     = 1,
                note         = f"결제방법: {body.payment_method or '미정'} / 금액: {amount:,}원",
            )
            db.add(unpaid)
            memo = f"[대여기기 미반납 청구] {loaner_name} / {amount:,}원 / {body.payment_method or '미정'}"
        else:
            memo = f"[대여기기 미반납 포기] {loaner_name}"

        lg.changed_value = {"decision": decision, "charge_amount": amount if decision == "청구" else 0}

        # AsCaseLog 기록
        log = AsCaseLog(
            as_case_id  = lg.as_case_id,
            from_status = None,
            to_status   = "대여기기미반납",
            staff_id    = current.id,
            memo        = memo,
        )
        db.add(log)

    await db.commit()
    await db.refresh(lg)
    return await _fetch_log(lg, db)


# ── 반려 ───────────────────────────────────────────────────────
@router.post("/{log_id}/reject")
async def reject_log(
    log_id: int,
    body: RejectBody,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[Staff, RequireGeneral],
):
    lg = await db.scalar(select(ApprovalLog).where(ApprovalLog.id == log_id))
    if not lg:
        raise HTTPException(404, "승인 건을 찾을 수 없습니다")
    if lg.status != ApprovalStatus.대기:
        raise HTTPException(400, "이미 처리된 건입니다")

    lg.status          = ApprovalStatus.반려
    lg.approved_by     = current.id
    lg.approved_at     = datetime.now(timezone.utc)
    lg.rejected_reason = body.reason or None

    # 대여기기미반납 반려 시 이력 기록
    if lg.exception_type == ExceptionType.대여기기미반납 and lg.as_case_id:
        loaner_name = (lg.original_value or {}).get("loaner_note", "대여 기기")
        log = AsCaseLog(
            as_case_id  = lg.as_case_id,
            from_status = None,
            to_status   = "대여기기미반납",
            staff_id    = current.id,
            memo        = f"[대여기기 미반납 요청 반려] {loaner_name} / {body.reason or '사유 없음'}",
        )
        db.add(log)

    await db.commit()
    await db.refresh(lg)
    return await _fetch_log(lg, db)
