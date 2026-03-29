"""기기 장부 모델"""
from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class DeviceStatus(str, enum.Enum):
    판매완료  = "판매완료"
    AS접수    = "AS접수"
    AS진행중  = "AS진행중"
    교환완료  = "교환완료"
    대여중    = "대여중"
    회수완료  = "회수완료"
    분실      = "분실"
    폐기      = "폐기"


class DeviceLedger(Base):
    __tablename__ = "device_ledgers"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    customer_id      = Column(Integer, ForeignKey("customers.id"), nullable=False)
    product_id       = Column(Integer, ForeignKey("products.id"), nullable=False)
    transaction_id   = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    sold_by_staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)

    color_option         = Column(String(50), nullable=True)
    purchase_price       = Column(Integer, nullable=True, comment="실제 구매 금액")
    is_discount_applied  = Column(Boolean, nullable=False, default=False,
                                  comment="기기 연동 할인가 적용 여부")

    status           = Column(Enum(DeviceStatus), nullable=False, default=DeviceStatus.판매완료)
    status_changed_at = Column(DateTime(timezone=True), nullable=True)
    status_note      = Column(Text, nullable=True)

    as_case_id       = Column(Integer, ForeignKey("as_cases.id"), nullable=True)
    exchange_case_id = Column(Integer, ForeignKey("exchange_cases.id"), nullable=True)
    purchased_at     = Column(DateTime(timezone=True), nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())

    customer      = relationship("Customer", back_populates="device_ledgers")
    product       = relationship("Product")
    transaction   = relationship("Transaction")
    sold_by       = relationship("Staff", foreign_keys=[sold_by_staff_id])
    as_case       = relationship("AsCase", foreign_keys=[as_case_id])
    exchange_case = relationship("ExchangeCase", foreign_keys=[exchange_case_id])

    def __repr__(self):
        return f"<DeviceLedger id={self.id} customer={self.customer_id} status={self.status}>"
