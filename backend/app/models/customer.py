"""고객 모델"""
from sqlalchemy import Column, Integer, SmallInteger, String, Boolean, DateTime, Text, func
from sqlalchemy.orm import relationship
from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    name            = Column(String(100), nullable=False)
    phone           = Column(String(20), nullable=False, unique=True)
    phone2          = Column(String(20), nullable=True)
    default_phone   = Column(SmallInteger, nullable=False, default=1, comment="기본 전화번호: 1=phone, 2=phone2")
    mileage_balance = Column(Integer, nullable=False, default=0)
    staff_memo      = Column(Text, nullable=True)
    address         = Column(Text, nullable=True, comment="기본 주소")
    address2        = Column(Text, nullable=True, comment="추가 주소")
    default_address = Column(SmallInteger, nullable=True, comment="기본 배송지: 1=address, 2=address2")
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
    def primary_phone(self):
        return self.phone2 if self.default_phone == 2 and self.phone2 else self.phone

    @property
    def primary_address(self):
        if self.default_address == 2 and self.address2:
            return self.address2
        return self.address

    def __repr__(self):
        return f"<Customer id={self.id} name={self.name} phone={self.phone}>"
