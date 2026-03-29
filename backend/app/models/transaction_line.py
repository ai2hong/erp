"""거래 상세 라인 모델 — DB 스키마에 맞춰 수정 (transaction_lines 테이블)"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class TransactionLine(Base):
    __tablename__ = "transaction_lines"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    product_id     = Column(Integer, ForeignKey("products.id"), nullable=True)

    quantity            = Column(Integer, nullable=False, default=1)
    unit_price          = Column(Integer, nullable=False, comment="적용 단가")
    line_total          = Column(Integer, nullable=False, comment="소계 = quantity × unit_price")
    is_device_discount  = Column(Boolean, nullable=False, default=False)
    is_service          = Column(Boolean, nullable=False, default=False)
    service_reason      = Column(String(200), nullable=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    transaction = relationship("Transaction", back_populates="lines")
    product     = relationship("Product", back_populates="transaction_lines")

    def __repr__(self):
        return f"<TxLine id={self.id} product={self.product_id} qty={self.quantity} total={self.line_total:,}>"
