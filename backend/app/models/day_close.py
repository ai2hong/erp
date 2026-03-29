"""일마감 모델 v2 — 직원 입력 + 시스템 자동 집계 분리

v2 변경:
- vip_count / vip_total 제거 (VIP 등급 폐지에 맞춰 삭제)
- discount_count / discount_total 추가 (직원 할인 거래 집계)
"""
from sqlalchemy import Column, Integer, Boolean, Enum, DateTime, Date, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class DayCloseStatus(str, enum.Enum):
    미제출   = "미제출"
    제출완료 = "제출완료"
    승인완료 = "승인완료"
    반려     = "반려"


class DayClose(Base):
    __tablename__ = "day_closes"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    close_date = Column(Date, nullable=False)
    store_id   = Column(Integer, nullable=False, default=1)
    status     = Column(Enum(DayCloseStatus), nullable=False, default=DayCloseStatus.미제출)

    # 직원 직접 입력
    actual_cash  = Column(Integer, nullable=True, comment="실제 현금 보유액")
    special_note = Column(Text, nullable=True, comment="특이사항")

    # 시스템 자동 집계
    tx_count             = Column(Integer, nullable=False, default=0)
    total_cash           = Column(Integer, nullable=False, default=0)
    total_transfer       = Column(Integer, nullable=False, default=0)
    total_card           = Column(Integer, nullable=False, default=0)
    total_mileage_used   = Column(Integer, nullable=False, default=0)
    total_mileage_earned = Column(Integer, nullable=False, default=0)
    total_store          = Column(Integer, nullable=False, default=0)
    total_delivery       = Column(Integer, nullable=False, default=0)
    total_shipping       = Column(Integer, nullable=False, default=0)
    device_count         = Column(Integer, nullable=False, default=0)
    service_count        = Column(Integer, nullable=False, default=0)
    unpaid_count         = Column(Integer, nullable=False, default=0)
    reservation_count    = Column(Integer, nullable=False, default=0)
    exchange_count       = Column(Integer, nullable=False, default=0)
    bonus_count          = Column(Integer, nullable=False, default=0)
    discount_count       = Column(Integer, nullable=False, default=0,
                                  comment="직원 할인 적용 거래 수")
    discount_total       = Column(Integer, nullable=False, default=0,
                                  comment="직원 할인 총액")
    normal_total         = Column(Integer, nullable=False, default=0)
    grand_total          = Column(Integer, nullable=False, default=0)
    loaner_active_count  = Column(Integer, nullable=False, default=0)
    cash_diff            = Column(Integer, nullable=True,
                                  comment="현금 차이 = actual_cash - total_cash")

    submitted_by    = Column(Integer, ForeignKey("staff.id"), nullable=True)
    submitted_at    = Column(DateTime(timezone=True), nullable=True)
    approved_by     = Column(Integer, ForeignKey("staff.id"), nullable=True)
    approved_at     = Column(DateTime(timezone=True), nullable=True)
    rejected_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    submitter = relationship("Staff", foreign_keys=[submitted_by])
    approver  = relationship("Staff", foreign_keys=[approved_by])

    def __repr__(self):
        return f"<DayClose date={self.close_date} status={self.status} total={self.grand_total:,}>"
