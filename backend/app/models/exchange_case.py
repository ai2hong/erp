"""교환 / 보상 / 환불 케이스 모델 — 남은 거래 전체 재산정 원칙"""
from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class CaseType(str, enum.Enum):
    액상교환 = "액상교환"
    코일교환 = "코일교환"
    기기교환 = "기기교환"
    보상지급 = "보상지급"
    부분환불 = "부분환불"
    전체환불 = "전체환불"


class CaseStatus(str, enum.Enum):
    접수중   = "접수중"
    처리중   = "처리중"
    승인대기 = "승인대기"
    완료     = "완료"
    반려     = "반려"


class ExchangeCase(Base):
    __tablename__ = "exchange_cases"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    case_number = Column(String(20), nullable=False, unique=True,
                         comment="케이스 번호. 예: EX-250315-001")

    customer_id     = Column(Integer, ForeignKey("customers.id"), nullable=False)
    original_tx_id  = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    staff_id        = Column(Integer, ForeignKey("staff.id"), nullable=False)
    approved_by     = Column(Integer, ForeignKey("staff.id"), nullable=True)

    case_type   = Column(Enum(CaseType), nullable=False)
    case_reason = Column(Text, nullable=False)
    status      = Column(Enum(CaseStatus), nullable=False, default=CaseStatus.접수중)

    return_product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    return_qty        = Column(Integer, nullable=False, default=0)
    return_condition  = Column(Text, nullable=True)
    give_product_id   = Column(Integer, ForeignKey("products.id"), nullable=True)
    give_qty          = Column(Integer, nullable=False, default=0)

    price_diff  = Column(Integer, nullable=False, default=0,
                         comment="차액. 양수=추가결제, 음수=환불")
    diff_method = Column(String(50), nullable=True)

    refund_recalc_snapshot = Column(JSON, nullable=True,
                                    comment="환불 후 남은 거래 재산정 결과 스냅샷")
    service_return_note    = Column(Text, nullable=True,
                                    comment="서비스 회수 불가 시 처리 메모")

    approval_log_id = Column(Integer, ForeignKey("approval_logs.id"), nullable=True)
    approved_at     = Column(DateTime(timezone=True), nullable=True)
    staff_memo      = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    customer       = relationship("Customer", back_populates="exchange_cases")
    original_tx    = relationship("Transaction", foreign_keys=[original_tx_id])
    staff          = relationship("Staff", foreign_keys=[staff_id])
    approver       = relationship("Staff", foreign_keys=[approved_by])
    return_product = relationship("Product", foreign_keys=[return_product_id])
    give_product   = relationship("Product", foreign_keys=[give_product_id])
    approval_log   = relationship("ApprovalLog", foreign_keys=[approval_log_id])

    def __repr__(self):
        return f"<ExchangeCase {self.case_number} type={self.case_type} status={self.status}>"
