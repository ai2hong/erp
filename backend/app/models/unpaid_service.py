"""미지급 서비스 모델"""
from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class UnpaidStatus(str, enum.Enum):
    미지급   = "미지급"
    지급완료 = "지급완료"
    취소     = "취소"


class UnpaidService(Base):
    __tablename__ = "unpaid_services"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    customer_id       = Column(Integer, ForeignKey("customers.id"), nullable=False)
    transaction_id    = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    service_record_id = Column(Integer, ForeignKey("service_records.id"), nullable=False)
    product_id        = Column(Integer, ForeignKey("products.id"), nullable=True,
                               comment="지급 예정 상품 (확정된 경우)")

    service_kind       = Column(String(50), nullable=False)
    selected_item      = Column(String(200), nullable=True)
    qty                = Column(Integer, nullable=False)
    undelivered_reason = Column(Text, nullable=True)

    status       = Column(Enum(UnpaidStatus), nullable=False, default=UnpaidStatus.미지급)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    processed_by = Column(Integer, ForeignKey("staff.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    customer       = relationship("Customer", back_populates="unpaid_services")
    transaction    = relationship("Transaction", back_populates="unpaid_services")
    service_record = relationship("ServiceRecord")
    product        = relationship("Product")
    staff          = relationship("Staff", foreign_keys=[processed_by])

    def __repr__(self):
        return f"<UnpaidService id={self.id} kind={self.service_kind} qty={self.qty} status={self.status}>"
