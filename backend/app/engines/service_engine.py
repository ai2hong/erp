"""
engines/service_engine.py — 서비스 자격 판별 엔진 v2

서비스(무상 제공) 규칙:
  - 액상 1병 → 서비스 1개 (액상서비스)
  - 액상 3병 → SET3 묶음 1개
  - 액상 4병 → SET3 묶음 1개 + 서비스 1개
  - 액상 6병 → SET3 묶음 2개
  - 기기만 → 기기 단독 증정 1개
  - 마일리지 전액 → 서비스 없음
  - 서비스 불가 거래(카드 등) → 서비스 없음
"""

from typing import Optional, List
from dataclasses import dataclass

from app.models.product import Product, DEVICE_ALL, LIQUID_ALL, LIQUID_EXCL


@dataclass
class ServiceItem:
    """개별 서비스 항목."""
    service_type: str          # "액상서비스", "SET3", "기기증정"
    quantity: int = 1
    note: Optional[str] = None


@dataclass
class ServiceResult:
    """서비스 판별 결과."""
    eligible: bool = False
    items: List[ServiceItem] = None
    note: Optional[str] = None

    def __post_init__(self):
        if self.items is None:
            self.items = []

    @property
    def total_count(self) -> int:
        return sum(i.quantity for i in self.items)


def calc_services(
    liquid_count: int,
    device_count: int,
    *,
    service_eligible: bool = True,
) -> ServiceResult:
    """
    서비스 품목 계산.

    Args:
        liquid_count: 액상 수량 (할인제외 포함, 서비스 품목 제외)
        device_count: 기기 수량
        service_eligible: 서비스 자격 여부 (price_engine에서 판별)

    Returns:
        ServiceResult
    """
    if not service_eligible:
        return ServiceResult(eligible=False, note="서비스 불가 거래")

    items = []

    # 기기 단독 증정
    if device_count > 0:
        items.append(ServiceItem(
            service_type="기기증정",
            quantity=device_count,
            note=f"기기 {device_count}대 구매 → 증정 {device_count}개",
        ))

    # 액상 서비스: SET3 묶음 우선, 나머지 개별
    if liquid_count > 0:
        set3_count = liquid_count // 3
        remaining = liquid_count % 3

        if set3_count > 0:
            items.append(ServiceItem(
                service_type="SET3",
                quantity=set3_count,
                note=f"액상 {set3_count * 3}병 → SET3 묶음 {set3_count}개",
            ))

        if remaining > 0:
            items.append(ServiceItem(
                service_type="액상서비스",
                quantity=remaining,
                note=f"액상 {remaining}병 → 서비스 {remaining}개",
            ))

    if not items:
        return ServiceResult(eligible=False, note="서비스 대상 없음")

    return ServiceResult(eligible=True, items=items)


def check_bonus_service(
    visit_count: int,
    total_purchase: int,
) -> Optional[str]:
    """
    단골 추가 서비스 판별.
    방문 10회 이상 + 누적 50만원 이상.
    """
    if visit_count >= 10 and total_purchase >= 500_000:
        return "단골 추가 서비스 대상"
    return None
