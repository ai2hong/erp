"""
models/device_ledger.py — 고객 기기 보유 이력

고객이 구매한 기기 기록. 교환·AS·대여 추적에 활용.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class DeviceLedger(Base):
    __tablename__ = "device_ledgers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False,
                        comment="구매한 기기 상품")
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True,
                            comment="구매 거래 ID")

    serial_number = Column(String(100), nullable=True, comment="기기 시리얼 번호")
    purchase_date = Column(DateTime(timezone=True), nullable=True, comment="구매일")

    # ── 상태 ────────────────────────────────────────────────
    is_active = Column(Boolean, nullable=False, default=True,
                       comment="현재 사용 중 여부. 교환·폐기 시 False.")
    is_loaner = Column(Boolean, nullable=False, default=False,
                       comment="대여 기기 여부")
    loaner_due_date = Column(DateTime(timezone=True), nullable=True,
                             comment="대여 반납 예정일")

    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ── 관계 ────────────────────────────────────────────────
    customer = relationship("Customer", back_populates="device_ledgers")
    product = relationship("Product")
    transaction = relationship("Transaction")

    def __repr__(self):
        status = "active" if self.is_active else "inactive"
        return f"<DeviceLedger customer={self.customer_id} product={self.product_id} [{status}]>"
