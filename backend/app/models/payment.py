"""
models/payment.py — 결제 수단 상세

거래(Transaction) 1건에 대한 결제 내역.
현금, 이체, 카드, 마일리지 등 복합 결제를 개별 행으로 기록.
"""

from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class PaymentMethod(str, enum.Enum):
    현금 = "현금"
    이체 = "이체"
    카드 = "카드"
    마일리지 = "마일리지"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)

    method = Column(Enum(PaymentMethod), nullable=False, comment="결제 수단")
    amount = Column(Integer, nullable=False, comment="결제 금액 (원)")
    memo = Column(String(200), nullable=True, comment="결제 메모. 예: 카드사명, 승인번호 등")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── 관계 ────────────────────────────────────────────────
    transaction = relationship("Transaction", back_populates="payments")

    def __repr__(self):
        return f"<Payment tx={self.transaction_id} method={self.method} amount={self.amount:,}>"
