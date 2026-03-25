"""
models/mileage_ledger.py — 적립금 원장

고객별 적립금 변동 이력.
적립, 사용, 수동조정, 정정 등 모든 변동을 기록.
"""

from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class MileageType(str, enum.Enum):
    적립 = "적립"           # 거래 완료 시 자동 적립
    사용 = "사용"           # 거래 시 적립금 차감
    수동조정 = "수동조정"   # 총괄·사장이 수동 조정
    정정 = "정정"           # 거래 정정으로 인한 변동
    환불 = "환불"           # 환불 시 적립금 회수


class MileageLedger(Base):
    __tablename__ = "mileage_ledgers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True,
                            comment="연관 거래 ID. 수동조정 시 NULL.")

    mileage_type = Column(Enum(MileageType), nullable=False)
    amount = Column(Integer, nullable=False,
                    comment="변동 금액 (원). 적립=양수, 사용/환불=음수.")
    balance_after = Column(Integer, nullable=False,
                           comment="변동 후 잔액 (원). 정합성 검증용.")
    note = Column(Text, nullable=True, comment="변동 사유 메모")

    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True,
                      comment="처리 직원. 수동조정 시 필수.")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── 관계 ────────────────────────────────────────────────
    customer = relationship("Customer", back_populates="mileage_ledgers")
    transaction = relationship("Transaction", back_populates="mileage_ledgers")
    staff = relationship("Staff", foreign_keys=[staff_id])

    def __repr__(self):
        return f"<MileageLedger customer={self.customer_id} type={self.mileage_type} amount={self.amount:,}>"
