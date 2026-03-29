"""결제 장부 모델"""
from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class PaymentMethod(str, enum.Enum):
    현금     = "현금"
    이체     = "이체"
    카드     = "카드"
    마일리지 = "마일리지"


class Payment(Base):
    __tablename__ = "payments"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    method         = Column(Enum(PaymentMethod), nullable=False)
    amount         = Column(Integer, nullable=False, comment="해당 수단 결제 금액 (원)")
    card_approval_no = Column(String(50), nullable=True, comment="카드 승인번호 수동 입력")
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    transaction = relationship("Transaction", back_populates="payments")

    def __repr__(self):
        return f"<Payment id={self.id} method={self.method} amount={self.amount:,}>"
