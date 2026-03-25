"""
models/service_record.py — 서비스(무상 제공) 기록

거래 시 발생한 서비스 품목 기록.
서비스 자격(service_eligible) 판별 후 자동 생성.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class ServiceRecord(Base):
    __tablename__ = "service_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True,
                        comment="서비스 제공 상품. 특정 상품이 아닌 경우 NULL.")

    service_type = Column(String(50), nullable=False,
                          comment="서비스 유형. 예: 액상서비스, 코일서비스, 단골추가")
    quantity = Column(Integer, nullable=False, default=1, comment="서비스 수량")
    estimated_cost = Column(Integer, nullable=True, default=0,
                            comment="서비스 추정 원가 (원). 비용 분석용.")
    note = Column(Text, nullable=True, comment="서비스 메모")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── 관계 ────────────────────────────────────────────────
    transaction = relationship("Transaction", back_populates="service_records")
    product = relationship("Product")

    def __repr__(self):
        return f"<ServiceRecord tx={self.transaction_id} type={self.service_type}>"
