"""
models/exchange_case.py — 교환 케이스

기기·상품 교환 요청 및 처리 이력.
매니저 이상 승인 필요.
"""

from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ExchangeStatus(str, enum.Enum):
    접수 = "접수"
    승인대기 = "승인대기"
    승인 = "승인"
    완료 = "완료"
    반려 = "반려"


class ExchangeCase(Base):
    __tablename__ = "exchange_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)

    # ── 원거래 ──────────────────────────────────────────────
    original_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False,
                                     comment="교환 대상 원거래")
    original_product_id = Column(Integer, ForeignKey("products.id"), nullable=False,
                                 comment="교환 대상 상품")

    # ── 교환 상품 ───────────────────────────────────────────
    new_product_id = Column(Integer, ForeignKey("products.id"), nullable=True,
                            comment="교환 후 새 상품. 미정이면 NULL.")
    new_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True,
                                comment="교환 후 새 거래 ID")

    # ── 상태·사유 ───────────────────────────────────────────
    status = Column(Enum(ExchangeStatus), nullable=False, default=ExchangeStatus.접수)
    reason = Column(Text, nullable=False, comment="교환 사유")
    amount_diff = Column(Integer, nullable=False, default=0,
                         comment="차액 (원). 양수=고객 추가 결제, 음수=환불.")

    # ── 처리 ────────────────────────────────────────────────
    requested_by = Column(Integer, ForeignKey("staff.id"), nullable=False)
    approved_by = Column(Integer, ForeignKey("staff.id"), nullable=True)
    approval_note = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # ── 관계 ────────────────────────────────────────────────
    customer = relationship("Customer", back_populates="exchange_cases")
    store = relationship("Store")
    original_tx = relationship("Transaction", foreign_keys=[original_transaction_id])
    original_product = relationship("Product", foreign_keys=[original_product_id])
    new_product = relationship("Product", foreign_keys=[new_product_id])
    new_tx = relationship("Transaction", foreign_keys=[new_transaction_id])
    requester = relationship("Staff", foreign_keys=[requested_by])
    approver = relationship("Staff", foreign_keys=[approved_by])

    def __repr__(self):
        return f"<ExchangeCase customer={self.customer_id} [{self.status}]>"
