"""미수령 모델"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class UnpaidService(Base):
    __tablename__ = "unpaid_services"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    customer_id    = Column(Integer, ForeignKey("customers.id"), nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)

    service_type = Column(String(100), nullable=False)
    quantity     = Column(Integer, nullable=False, default=1)
    note         = Column(Text, nullable=True)
    is_fulfilled = Column(Boolean, nullable=False, default=False)

    fulfilled_at             = Column(DateTime(timezone=True), nullable=True)
    fulfilled_by             = Column(Integer, ForeignKey("staff.id"), nullable=True)
    fulfilled_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer    = relationship("Customer", back_populates="unpaid_services")
    transaction = relationship("Transaction", back_populates="unpaid_services", foreign_keys=[transaction_id])

    def __repr__(self):
        return f"<UnpaidService id={self.id} type={self.service_type} fulfilled={self.is_fulfilled}>"
