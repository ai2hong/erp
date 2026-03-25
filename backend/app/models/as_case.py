"""
models/as_case.py — A/S(애프터서비스) 케이스

기기 불량·고장 접수 및 처리 이력.
"""

from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class AsCaseStatus(str, enum.Enum):
    접수 = "접수"
    진행중 = "진행중"
    완료 = "완료"
    반품 = "반품"       # 제조사 반품
    취소 = "취소"


class AsCase(Base):
    __tablename__ = "as_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)

    # ── 기기 정보 ───────────────────────────────────────────
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False,
                        comment="A/S 대상 기기")
    device_ledger_id = Column(Integer, ForeignKey("device_ledgers.id"), nullable=True,
                              comment="고객 기기 보유 이력 참조")
    serial_number = Column(String(100), nullable=True, comment="기기 시리얼 번호")

    # ── 증상·처리 ───────────────────────────────────────────
    symptom = Column(Text, nullable=False, comment="고장·불량 증상")
    diagnosis = Column(Text, nullable=True, comment="진단 내용")
    resolution = Column(Text, nullable=True, comment="처리 결과")

    # ── 대여 기기 ───────────────────────────────────────────
    loaner_product_id = Column(Integer, ForeignKey("products.id"), nullable=True,
                               comment="대여 기기. 없으면 NULL.")
    loaner_out_date = Column(DateTime(timezone=True), nullable=True,
                             comment="대여 출고일")
    loaner_return_date = Column(DateTime(timezone=True), nullable=True,
                                comment="대여 반납일")

    # ── 상태 ────────────────────────────────────────────────
    status = Column(Enum(AsCaseStatus), nullable=False, default=AsCaseStatus.접수)
    received_by = Column(Integer, ForeignKey("staff.id"), nullable=False,
                         comment="접수 직원")
    completed_by = Column(Integer, ForeignKey("staff.id"), nullable=True,
                          comment="완료 처리 직원")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ── 관계 ────────────────────────────────────────────────
    customer = relationship("Customer", back_populates="as_cases")
    store = relationship("Store")
    product = relationship("Product", foreign_keys=[product_id])
    device_ledger = relationship("DeviceLedger")
    loaner_product = relationship("Product", foreign_keys=[loaner_product_id])
    receiver = relationship("Staff", foreign_keys=[received_by])
    completer = relationship("Staff", foreign_keys=[completed_by])

    def __repr__(self):
        return f"<AsCase customer={self.customer_id} product={self.product_id} [{self.status}]>"
