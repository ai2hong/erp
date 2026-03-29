"""적립금 원장 모델"""
from sqlalchemy import Column, Integer, Enum, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class MileageType(str, enum.Enum):
    적립       = "적립"
    사용       = "사용"
    회수       = "회수"
    재적립     = "재적립"
    수동조정   = "수동조정"
    마이너스조정 = "마이너스조정"


class MileageLedger(Base):
    __tablename__ = "mileage_ledgers"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    customer_id    = Column(Integer, ForeignKey("customers.id"), nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    mileage_type   = Column(Enum(MileageType), nullable=False)
    amount         = Column(Integer, nullable=False)
    balance_after  = Column(Integer, nullable=False)
    note           = Column(Text, nullable=True)
    staff_id       = Column(Integer, ForeignKey("staff.id"), nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    customer    = relationship("Customer", back_populates="mileage_ledgers")
    transaction = relationship("Transaction", back_populates="mileage_ledgers")
    staff       = relationship("Staff", foreign_keys=[staff_id])

    def __repr__(self):
        return f"<MileageLedger id={self.id} type={self.mileage_type} amount={self.amount:+,}>"
