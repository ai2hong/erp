"""서비스 기록 모델 — DB 스키마에 맞춰 수정 (service_records 테이블)"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class ServiceRecord(Base):
    __tablename__ = "service_records"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    product_id     = Column(Integer, ForeignKey("products.id"), nullable=True)

    service_type    = Column(String(100), nullable=False)
    quantity        = Column(Integer, nullable=False, default=1)
    estimated_cost  = Column(Integer, nullable=False, default=0)
    note            = Column(Text, nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    transaction = relationship("Transaction", back_populates="service_records")
    product     = relationship("Product", foreign_keys=[product_id])

    def __repr__(self):
        return f"<ServiceRecord id={self.id} type={self.service_type} qty={self.quantity}>"
