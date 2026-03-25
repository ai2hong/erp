"""
models/day_close.py — 일마감 모델 v3

v3 변경사항:
  - opening_cash (개점 시재금) 컬럼 추가  → 시재금 관리 기능
  - cash_diff 계산: actual_cash - total_cash - opening_cash
  - vip_count / vip_total 컬럼 삭제 (VIP 기능 제거됨)
  - discount_total 컬럼 추가 (직원 할인 합계)
  - store_id → ForeignKey("stores.id") 로 변경
  - UniqueConstraint("close_date", "store_id") 추가 → 날짜+매장 중복 방지
"""

from typing import Optional

from sqlalchemy import (
    Column, Integer, Boolean, Enum, DateTime,
    Date, Text, ForeignKey, UniqueConstraint, func
)
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class DayCloseStatus(str, enum.Enum):
    미제출   = "미제출"
    제출완료 = "제출완료"
    승인완료 = "승인완료"
    반려     = "반려"


class DayClose(Base):
    """
    일마감 모델.

    흐름:
      1. 개점 시 매니저가 opening_cash 입력 (시재금)
      2. 영업 중 시스템이 거래 집계 자동 갱신
      3. 마감 시 actual_cash(실사 현금) 입력
      4. cash_diff = actual_cash - (opening_cash + total_cash) 자동 계산
      5. 매니저 제출 → 총괄/사장 승인

    UniqueConstraint: 날짜 + 매장 조합이 유일 → 이중 마감 방지
    """
    __tablename__ = "day_closes"
    __table_args__ = (
        UniqueConstraint("close_date", "store_id", name="uq_dayclose_date_store"),
    )

    id         = Column(Integer, primary_key=True, autoincrement=True)
    close_date = Column(Date, nullable=False, comment="마감 날짜")
    store_id   = Column(Integer, ForeignKey("stores.id"), nullable=False, comment="매장")
    status     = Column(Enum(DayCloseStatus), nullable=False, default=DayCloseStatus.미제출)

    # ── 직원 직접 입력 ───────────────────────────────────────
    opening_cash = Column(Integer, nullable=True, default=0,
                          comment=(
                              "개점 시재금 (원). "
                              "개점 시 매니저가 입력. "
                              "현금 차이 계산 기준점: actual_cash - (opening_cash + total_cash)"
                          ))
    actual_cash  = Column(Integer, nullable=True,
                          comment="마감 시 실제 현금 보유액 (원). 직원 직접 실사 후 입력.")
    special_note = Column(Text, nullable=True, comment="특이사항 메모")

    # ── 시스템 자동 집계 ─────────────────────────────────────
    tx_count             = Column(Integer, nullable=False, default=0, comment="총 거래 건수")
    total_cash           = Column(Integer, nullable=False, default=0, comment="현금 합계")
    total_transfer       = Column(Integer, nullable=False, default=0, comment="이체 합계")
    total_card           = Column(Integer, nullable=False, default=0, comment="카드 합계")
    total_mileage_used   = Column(Integer, nullable=False, default=0, comment="적립금 사용 합계")
    total_mileage_earned = Column(Integer, nullable=False, default=0, comment="적립금 적립 합계")
    total_discount       = Column(Integer, nullable=False, default=0,
                                  comment="직원 할인 합계 (원). discount_amount 집계.")
    total_store          = Column(Integer, nullable=False, default=0, comment="매장 채널 매출")
    total_delivery       = Column(Integer, nullable=False, default=0, comment="배달 채널 매출")
    total_shipping       = Column(Integer, nullable=False, default=0, comment="택배 채널 매출")
    grand_total          = Column(Integer, nullable=False, default=0,
                                  comment="총 매출 = total_store + total_delivery + total_shipping")

    device_count      = Column(Integer, nullable=False, default=0, comment="기기 판매 대수")
    service_count     = Column(Integer, nullable=False, default=0, comment="서비스 발생 건수")
    unpaid_count      = Column(Integer, nullable=False, default=0, comment="미지급 서비스 건수")
    reservation_count = Column(Integer, nullable=False, default=0, comment="예약 처리 건수")
    exchange_count    = Column(Integer, nullable=False, default=0, comment="교환·환불 건수")
    bonus_count       = Column(Integer, nullable=False, default=0, comment="단골 추가 서비스 건수")
    discount_count    = Column(Integer, nullable=False, default=0, comment="할인 거래 건수")
    loaner_active_count = Column(Integer, nullable=False, default=0, comment="대여 중인 기기 수")

    # ── 현금 차이 (자동 계산) ────────────────────────────────
    cash_diff = Column(Integer, nullable=True,
                       comment=(
                           "현금 차이 (원). "
                           "= actual_cash - (opening_cash + total_cash + total_transfer). "
                           "양수 = 초과, 음수 = 부족. "
                           "마감 제출 시 서버에서 자동 계산."
                       ))

    # ── 제출·승인 ────────────────────────────────────────────
    submitted_by    = Column(Integer, ForeignKey("staff.id"), nullable=True)
    submitted_at    = Column(DateTime(timezone=True), nullable=True)
    approved_by     = Column(Integer, ForeignKey("staff.id"), nullable=True)
    approved_at     = Column(DateTime(timezone=True), nullable=True)
    rejected_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    store     = relationship("Store")
    submitter = relationship("Staff", foreign_keys=[submitted_by])
    approver  = relationship("Staff", foreign_keys=[approved_by])

    # ── 편의 프로퍼티 ────────────────────────────────────────
    @property
    def expected_cash(self) -> int:
        """
        예상 보유 현금 = 개점 시재금 + 현금 매출 + 이체 매출.
        이체는 실물 현금이 아니지만 소규모 매장에서는 시재금에 합산하는 경우가 많음.
        실제 운영 방식에 따라 계산식 조정 가능.
        """
        return (self.opening_cash or 0) + self.total_cash

    @property
    def computed_cash_diff(self) -> Optional[int]:
        """actual_cash - expected_cash. actual_cash 미입력 시 None."""
        if self.actual_cash is None:
            return None
        return self.actual_cash - self.expected_cash

    def __repr__(self):
        return (f"<DayClose date={self.close_date} store={self.store_id} "
                f"status={self.status} total={self.grand_total:,}>")
