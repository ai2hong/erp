"""
models/reservation.py — 상품 예약

품절 상품 입고 시 고객에게 연락하기 위한 예약 관리.
"""

from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ReservationStatus(str, enum.Enum):
    대기 = "대기"       # 예약 접수, 입고 대기
    입고완료 = "입고완료"   # 상품 입고됨, 고객 연락 필요
    완료 = "완료"       # 고객 수령 완료
    취소 = "취소"       # 예약 취소


class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)

    status = Column(Enum(ReservationStatus), nullable=False,
                    default=ReservationStatus.대기)
    quantity = Column(Integer, nullable=False, default=1)
    note = Column(Text, nullable=True, comment="예약 메모")

    # ── 처리 ────────────────────────────────────────────────
    reserved_by = Column(Integer, ForeignKey("staff.id"), nullable=False,
                         comment="예약 접수 직원")
    fulfilled_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True,
                                      comment="수령 시 거래 ID")
    contacted_at = Column(DateTime(timezone=True), nullable=True,
                          comment="고객 연락 시각")
    fulfilled_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ── 관계 ────────────────────────────────────────────────
    customer = relationship("Customer", back_populates="reservations")
    product = relationship("Product")
    store = relationship("Store")
    reserved_staff = relationship("Staff", foreign_keys=[reserved_by])
    fulfilled_tx = relationship("Transaction", foreign_keys=[fulfilled_transaction_id])

    def __repr__(self):
        return f"<Reservation customer={self.customer_id} product={self.product_id} [{self.status}]>"
