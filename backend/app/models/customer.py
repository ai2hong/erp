"""
models/customer.py — 고객 장부 모델 v3

v3 변경사항:
  - preferred_liquid    (선호 액상 메모) 컬럼 추가
  - preferred_nicotine  (선호 니코틴 농도) 컬럼 추가
  - preferred_device    (사용 기기) 컬럼 추가
  - staff_memo          이미 존재 — 이제 UI에서 편집 가능
  - avg_visit_interval  property 추가 (방문 패턴 분석)
  - is_long_absent      property 추가 (장기 미방문 감지)

기존 제거된 항목:
  - is_vip, vip_note (VIP 기능 완전 제거됨, v2에서 이미 제거)
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, func
from sqlalchemy.orm import relationship
from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id    = Column(Integer, primary_key=True, autoincrement=True)
    name  = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False, unique=True,
                   comment="전화번호. 고객 식별 키. 중복 불가.")

    # ── 적립금 ──────────────────────────────────────────────
    mileage_balance = Column(Integer, nullable=False, default=0,
                             comment="적립금 잔액 (원). 마이너스 허용. 10원 단위.")

    # ── 고객 메모 / 선호 정보 (직원 기록용) ─────────────────
    staff_memo = Column(Text, nullable=True,
                        comment=(
                            "직원 내부 메모. 고객에게 공개 안 됨. "
                            "예: '기기 교체 고민 중', '매주 화요일 방문' 등."
                        ))
    preferred_liquid  = Column(String(300), nullable=True,
                                comment=(
                                    "선호 액상 메모. "
                                    "예: '입이벤트 아이스 계열 선호, 베이프독 민트 단골'"
                                ))
    preferred_nicotine = Column(String(50), nullable=True,
                                 comment="선호 니코틴 농도. 예: '9mg', '3mg', '소금 50mg'")
    preferred_device   = Column(String(200), nullable=True,
                                 comment=(
                                     "현재 사용 기기. "
                                     "예: '위넥스 H1 블랙 + 발라리안 클로즈팟 0.6옴'"
                                 ))

    # ── 방문 집계 ────────────────────────────────────────────
    last_visit_at  = Column(DateTime(timezone=True), nullable=True,
                            comment="마지막 방문 일시. 거래 완료 시 자동 갱신.")
    total_purchase = Column(Integer, nullable=False, default=0,
                            comment="누적 구매 금액 (원). 거래 완료 시 자동 갱신.")
    visit_count    = Column(Integer, nullable=False, default=0,
                            comment="총 방문 횟수. 거래 완료 시 자동 갱신.")

    # ── 상태 ─────────────────────────────────────────────────
    is_deleted = Column(Boolean, nullable=False, default=False,
                        comment="소프트 삭제. True면 조회에서 제외.")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ── 관계 ────────────────────────────────────────────────
    mileage_ledgers = relationship("MileageLedger", back_populates="customer",
                                   order_by="MileageLedger.created_at.desc()")
    transactions    = relationship("Transaction", back_populates="customer",
                                   order_by="Transaction.created_at.desc()")
    device_ledgers  = relationship("DeviceLedger", back_populates="customer")
    unpaid_services = relationship("UnpaidService", back_populates="customer")
    reservations    = relationship("Reservation", back_populates="customer")
    exchange_cases  = relationship("ExchangeCase", back_populates="customer")
    as_cases        = relationship("AsCase", back_populates="customer")

    # ── 적립금 프로퍼티 ──────────────────────────────────────
    @property
    def is_negative_mileage(self) -> bool:
        return self.mileage_balance < 0

    # ── 방문 패턴 분석 프로퍼티 ──────────────────────────────

    @property
    def days_since_last_visit(self) -> Optional[int]:
        """
        마지막 방문 이후 경과 일수.
        방문 이력 없으면 None.
        """
        if not self.last_visit_at:
            return None
        now = datetime.now(timezone.utc)
        lv = self.last_visit_at
        if lv.tzinfo is None:
            lv = lv.replace(tzinfo=timezone.utc)
        return (now - lv).days

    @property
    def is_long_absent(self) -> bool:
        """
        장기 미방문 여부 (30일 이상).
        단골 관리 화면에서 장기 미방문 고객 목록 필터링에 사용.
        기준일은 운영 정책에 따라 조정 가능.
        """
        days = self.days_since_last_visit
        if days is None:
            return False
        return days >= 30

    @property
    def avg_purchase_per_visit(self) -> Optional[int]:
        """
        방문당 평균 구매 금액 (원).
        방문 횟수 0이면 None.
        """
        if not self.visit_count:
            return None
        return self.total_purchase // self.visit_count

    @property
    def visit_frequency_label(self) -> str:
        """
        방문 빈도 레이블.
        transactions 관계가 로드된 상태에서 호출해야 정확함.
        빠른 표시용 — 정확한 분석은 API에서 집계 쿼리 사용.

        기준:
          주 2회+ → 단골
          주 1회  → 일반
          월 1회  → 가끔
          30일+   → 장기미방문
          방문없음 → 신규
        """
        days = self.days_since_last_visit
        if days is None or self.visit_count == 0:
            return "신규"
        if days >= 30:
            return "장기미방문"

        # visit_count와 created_at 기반 대략적 계산
        if self.created_at:
            ca = self.created_at
            if ca.tzinfo is None:
                ca = ca.replace(tzinfo=timezone.utc)
            total_days = max(1, (datetime.now(timezone.utc) - ca).days)
            visits_per_week = self.visit_count / (total_days / 7)
            if visits_per_week >= 2:
                return "단골"
            elif visits_per_week >= 1:
                return "일반"
            else:
                return "가끔"
        return "일반"

    def __repr__(self):
        return f"<Customer id={self.id} name={self.name} phone={self.phone}>"
