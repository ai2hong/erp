"""예약 주문 모델"""
from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ReservationStatus(str, enum.Enum):
    예약접수   = "예약접수"
    예약금결제 = "예약금결제"
    입고대기   = "입고대기"
    입고완료   = "입고완료"
    고객통보   = "고객통보"
    수령완료   = "수령완료"
    취소       = "취소"
    환불완료   = "환불완료"


class Reservation(Base):
    __tablename__ = "reservations"

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    reservation_number = Column(String(20), nullable=False, unique=True,
                                comment="예약번호. 예: R-250315-001")
    customer_id  = Column(Integer, ForeignKey("customers.id"), nullable=False)
    product_id   = Column(Integer, ForeignKey("products.id"), nullable=True)
    staff_id     = Column(Integer, ForeignKey("staff.id"), nullable=False)

    qty          = Column(Integer, nullable=False, default=1)
    option_memo  = Column(Text, nullable=True, comment="색상·용량 등 자유 입력")

    is_prepaid      = Column(Boolean, nullable=False, default=False)
    prepaid_amount  = Column(Integer, nullable=False, default=0)
    prepaid_at      = Column(DateTime(timezone=True), nullable=True)
    prepaid_tx_id   = Column(Integer, ForeignKey("transactions.id"), nullable=True)

    status          = Column(Enum(ReservationStatus), nullable=False,
                             default=ReservationStatus.예약접수)
    inbound_move_id = Column(Integer, ForeignKey("inventory_moves.id"), nullable=True)
    notified_at     = Column(DateTime(timezone=True), nullable=True)
    received_at     = Column(DateTime(timezone=True), nullable=True)
    final_tx_id     = Column(Integer, ForeignKey("transactions.id"), nullable=True)

    cancelled_at   = Column(DateTime(timezone=True), nullable=True)
    cancel_reason  = Column(Text, nullable=True)
    refund_amount  = Column(Integer, nullable=False, default=0)
    staff_memo     = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    customer   = relationship("Customer", back_populates="reservations")
    product    = relationship("Product")
    staff      = relationship("Staff", foreign_keys=[staff_id])
    prepaid_tx = relationship("Transaction", foreign_keys=[prepaid_tx_id])
    final_tx   = relationship("Transaction", foreign_keys=[final_tx_id])

    def __repr__(self):
        return f"<Reservation {self.reservation_number} status={self.status}>"
