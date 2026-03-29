"""예약 주문 모델"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class Reservation(Base):
    __tablename__ = "reservations"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    store_id    = Column(Integer, ForeignKey("stores.id"), nullable=True)
    product_id  = Column(Integer, ForeignKey("products.id"), nullable=True)

    quantity    = Column(Integer, nullable=False, default=1)
    status      = Column(String(30), nullable=False, default="예약접수")
    note        = Column(Text, nullable=True)

    reserved_by              = Column(Integer, ForeignKey("staff.id"), nullable=True)
    contacted_at             = Column(DateTime(timezone=True), nullable=True)
    fulfilled_at             = Column(DateTime(timezone=True), nullable=True)
    fulfilled_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    customer = relationship("Customer", back_populates="reservations")

    def __repr__(self):
        return f"<Reservation id={self.id} status={self.status}>"
