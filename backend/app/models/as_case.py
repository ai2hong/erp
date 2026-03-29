"""AS 케이스 모델"""
from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class AsStatus(str, enum.Enum):
    접수      = "접수"
    점검중    = "점검중"
    제조사전달 = "제조사전달"
    수리완료  = "수리완료"
    반환완료  = "반환완료"
    반려      = "반려"


class AsCase(Base):
    __tablename__ = "as_cases"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    customer_id      = Column(Integer, ForeignKey("customers.id"), nullable=False)
    store_id         = Column(Integer, ForeignKey("stores.id"), nullable=True)
    product_id       = Column(Integer, ForeignKey("products.id"), nullable=True)
    device_ledger_id = Column(Integer, ForeignKey("device_ledgers.id"), nullable=True)
    serial_number    = Column(String(100), nullable=True)

    symptom    = Column(Text, nullable=True)
    diagnosis  = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)
    status     = Column(String(20), nullable=False, default="접수")

    received_by  = Column(Integer, ForeignKey("staff.id"), nullable=True)
    completed_by = Column(Integer, ForeignKey("staff.id"), nullable=True)

    loaner_product_id  = Column(Integer, ForeignKey("products.id"), nullable=True)
    loaner_out_date    = Column(DateTime(timezone=True), nullable=True)
    loaner_return_date = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    customer = relationship("Customer", back_populates="as_cases")

    def __repr__(self):
        return f"<AsCase id={self.id} status={self.status}>"
