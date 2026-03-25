"""
models/transaction_line.py — 거래 상세 품목 (라인 아이템)

거래(Transaction) 1건에 대한 개별 상품 라인.
수량, 단가, 할인가, 소계 등을 기록.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class TransactionLine(Base):
    __tablename__ = "transaction_lines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    # ── 수량·가격 ──────────────────────────────────────────
    quantity = Column(Integer, nullable=False, default=1, comment="수량")
    unit_price = Column(Integer, nullable=False, comment="적용 단가 (원). 정상가 또는 기기할인가.")
    line_total = Column(Integer, nullable=False, comment="라인 소계 = unit_price × quantity")

    # ── 기기 연동 할인 적용 여부 ────────────────────────────
    is_device_discount = Column(Boolean, nullable=False, default=False,
                                comment="기기 연동 할인가 적용 여부")

    # ── 서비스 관련 ─────────────────────────────────────────
    is_service = Column(Boolean, nullable=False, default=False,
                        comment="서비스(무료 제공) 품목 여부")
    service_reason = Column(String(200), nullable=True,
                            comment="서비스 사유. is_service=True일 때 기록.")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── 관계 ────────────────────────────────────────────────
    transaction = relationship("Transaction", back_populates="lines")
    product = relationship("Product", back_populates="transaction_lines")

    def __repr__(self):
        return f"<TransactionLine tx={self.transaction_id} product={self.product_id} qty={self.quantity}>"
