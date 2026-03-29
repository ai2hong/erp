"""AS 케이스 모델"""
from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class AsStatus(str, enum.Enum):
    접수   = "접수"
    처리중 = "처리중"
    AS완료 = "AS완료"


class AsCase(Base):
    __tablename__ = "as_cases"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    customer_id      = Column(Integer, ForeignKey("customers.id"), nullable=False)
    store_id         = Column(Integer, ForeignKey("stores.id"), nullable=True)
    product_id       = Column(Integer, ForeignKey("products.id"), nullable=True)
    device_ledger_id = Column(Integer, ForeignKey("device_ledgers.id"), nullable=True)
    serial_number    = Column(String(100), nullable=True)

    symptom    = Column(Text, nullable=False, default="")
    diagnosis  = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)
    status     = Column(Enum(AsStatus, name="ascasestatus", create_type=False), nullable=False, default=AsStatus.접수)

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
