"""
models/unpaid_service.py — 미지급 서비스 관리

서비스 자격은 있지만 현장에서 바로 제공하지 못한 경우 기록.
고객 다음 방문 시 제공하기 위한 추적 테이블.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class UnpaidService(Base):
    __tablename__ = "unpaid_services"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False,
                            comment="서비스 자격이 발생한 원거래")

    service_type = Column(String(50), nullable=False,
                          comment="미지급 서비스 유형. 예: 액상서비스, 코일서비스")
    quantity = Column(Integer, nullable=False, default=1)
    note = Column(Text, nullable=True, comment="미지급 사유 등")

    # ── 정산 ────────────────────────────────────────────────
    is_fulfilled = Column(Boolean, nullable=False, default=False,
                          comment="제공 완료 여부")
    fulfilled_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True,
                                      comment="서비스 제공한 거래 ID")
    fulfilled_at = Column(DateTime(timezone=True), nullable=True)
    fulfilled_by = Column(Integer, ForeignKey("staff.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── 관계 ────────────────────────────────────────────────
    customer = relationship("Customer", back_populates="unpaid_services")
    transaction = relationship("Transaction", back_populates="unpaid_services",
                               foreign_keys=[transaction_id])
    fulfilled_tx = relationship("Transaction", foreign_keys=[fulfilled_transaction_id])
    fulfilled_staff = relationship("Staff", foreign_keys=[fulfilled_by])

    def __repr__(self):
        status = "완료" if self.is_fulfilled else "미지급"
        return f"<UnpaidService customer={self.customer_id} type={self.service_type} [{status}]>"
