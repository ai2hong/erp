"""
고객 장부 모델 v2
- VIP/단골 등급 완전 제거 (is_vip, vip_note 삭제)
- 고객은 단순 고객으로만 관리
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, func
from sqlalchemy.orm import relationship
from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    name            = Column(String(100), nullable=False)
    phone           = Column(String(20), nullable=False, unique=True)
    mileage_balance = Column(Integer, nullable=False, default=0,
                             comment="적립금 잔액. 마이너스 허용. 10원 단위.")
    staff_memo      = Column(Text, nullable=True, comment="직원 메모 (내부용)")
    last_visit_at   = Column(DateTime(timezone=True), nullable=True)
    total_purchase  = Column(Integer, nullable=False, default=0)
    visit_count     = Column(Integer, nullable=False, default=0)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted      = Column(Boolean, nullable=False, default=False)

    mileage_ledgers = relationship("MileageLedger", back_populates="customer",
                                   order_by="MileageLedger.created_at.desc()")
    transactions    = relationship("Transaction", back_populates="customer",
                                   order_by="Transaction.created_at.desc()")
    device_ledgers  = relationship("DeviceLedger", back_populates="customer")
    unpaid_services = relationship("UnpaidService", back_populates="customer")
    reservations    = relationship("Reservation", back_populates="customer")
    exchange_cases  = relationship("ExchangeCase", back_populates="customer")
    as_cases        = relationship("AsCase", back_populates="customer")

    @property
    def is_negative_mileage(self): return self.mileage_balance < 0

    def __repr__(self):
        return f"<Customer id={self.id} name={self.name} phone={self.phone}>"
