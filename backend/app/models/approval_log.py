"""
예외 승인 로그 모델 v2
- VIP예외가격 → 할인적용으로 변경
"""
from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ExceptionType(str, enum.Enum):
    할인적용     = "할인적용"      # 기존 VIP예외가격 대체. 직원 할인 입력 모두 포함.
    기기할인3대이상 = "기기할인3대이상"
    적립금수동조정  = "적립금수동조정"
    재고조정      = "재고조정"
    환불승인      = "환불승인"
    교환승인      = "교환승인"
    매장간이동    = "매장간이동"
    일마감정정    = "일마감정정"
    회원삭제      = "회원삭제"
    대여기기미반납 = "대여기기미반납"
    기타          = "기타"


class ApprovalStatus(str, enum.Enum):
    대기 = "대기"
    승인 = "승인"
    반려 = "반려"


class ApprovalLog(Base):
    __tablename__ = "approval_logs"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    log_number = Column(String(20), nullable=False, unique=True)

    exception_type   = Column(Enum(ExceptionType), nullable=False)
    status           = Column(Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.대기)
    original_value   = Column(JSON, nullable=True)
    changed_value    = Column(JSON, nullable=True)
    exception_reason = Column(Text, nullable=False, comment="사유. 필수.")

    # 할인적용 전용
    discount_amount = Column(Integer, nullable=True,
                             comment="할인 금액 (원). 할인적용 타입만.")

    requested_by     = Column(Integer, ForeignKey("staff.id"), nullable=False)
    approved_by      = Column(Integer, ForeignKey("staff.id"), nullable=True)
    transaction_id   = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    exchange_case_id = Column(Integer, ForeignKey("exchange_cases.id"), nullable=True)
    day_close_id     = Column(Integer, ForeignKey("day_closes.id"), nullable=True)
    customer_id      = Column(Integer, ForeignKey("customers.id"), nullable=True)
    as_case_id       = Column(Integer, ForeignKey("as_cases.id"), nullable=True)

    requested_at    = Column(DateTime(timezone=True), server_default=func.now())
    approved_at     = Column(DateTime(timezone=True), nullable=True)
    rejected_reason = Column(Text, nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    requester     = relationship("Staff", foreign_keys=[requested_by])
    approver      = relationship("Staff", foreign_keys=[approved_by])
    transaction   = relationship("Transaction", foreign_keys=[transaction_id])
    exchange_case = relationship("ExchangeCase", foreign_keys=[exchange_case_id])
    customer      = relationship("Customer", foreign_keys=[customer_id])

    def __repr__(self):
        return f"<ApprovalLog {self.log_number} type={self.exception_type} status={self.status}>"
