"""
engines/price_engine.py — 가격 계산 엔진 v2

기준서 v8 기반 묶음 할인 + 연동 할인 + 적립금 계산.

핵심 규칙:
  - 3병 묶음 할인: 할인제외 제외한 전체 액상 3병 이상 시 적용
    - 묶음 기본가: 50,000 (이벤트만으로 구성 시)
    - 일반 액상이 묶음에 포함 시: +5,000/병 추가
    - 이벤트 우선 소진 → 남은 자리를 일반이 채움
  - 폐이벤트 2병 묶음: 45,000 (3병 묶음 이후 잔여에 적용)
  - 할인제외 상품: 항상 정가 (묶음 대상 제외)
  - 기기 연동 할인: 기기 구매 시 device_discount_price 적용
  - 적립: 이체/현금 결제 시 결제금액의 1% (10원 단위 절사)
"""

from typing import Optional, List
from dataclasses import dataclass, field

from app.models.product import (
    Product, ProductCategory,
    LIQUID_ALL, LIQUID_EXCL, DEVICE_LINKED, DEVICE_FIXED, DEVICE_ALL, HIGH_POD,
)


# ── 가격 상수 ──────────────────────────────────────────────
BUNDLE_3_BASE    = 50_000   # 3병 묶음 기본가 (이벤트만)
BUNDLE_3_NORMAL  = 5_000    # 3병 묶음 내 일반 1병당 추가금
BUNDLE_2_폐      = 45_000   # 폐이벤트 2병 묶음가
입이벤트_단가     = 20_000
폐이벤트_단가     = 25_000


@dataclass
class LineCalcResult:
    """개별 라인 계산 결과."""
    product_id: int
    quantity: int
    unit_price: int
    line_total: int
    is_device_discount: bool = False
    is_service: bool = False


@dataclass
class CartCalcResult:
    """장바구니 전체 계산 결과."""
    lines: List[LineCalcResult] = field(default_factory=list)
    subtotal: int = 0
    has_device: bool = False
    has_high_pod: bool = False
    event_discount_applied: int = 0


def get_unit_price(product: Product, *, with_device_discount: bool = False) -> int:
    """상품 단가 결정."""
    if with_device_discount and product.is_device_linked:
        return product.safe_device_price
    return product.normal_price


def calc_line_total(product: Product, quantity: int, *, with_device_discount: bool = False) -> int:
    """라인 소계 = 단가 x 수량."""
    return get_unit_price(product, with_device_discount=with_device_discount) * quantity


def calc_cart(products_with_qty: List[tuple]) -> CartCalcResult:
    """
    장바구니 전체 계산 — 묶음 할인 적용.

    Args:
        products_with_qty: [(product, quantity), ...] 리스트

    Returns:
        CartCalcResult
    """
    result = CartCalcResult()
    has_device = False
    has_high_pod = False

    # 분류별 수집
    event_입_items = []   # (product, qty)
    event_폐_items = []
    normal_items = []     # 일반 액상 (할인제외 아닌)
    excluded_items = []   # 할인제외
    device_items = []
    other_items = []      # 코일, 악세사리 등

    for product, qty in products_with_qty:
        if product.category in DEVICE_ALL:
            has_device = True
            device_items.append((product, qty))
        elif product.category in HIGH_POD:
            has_high_pod = True
            other_items.append((product, qty))
        elif product.category in LIQUID_EXCL:
            excluded_items.append((product, qty))
        elif product.category == ProductCategory.입호흡_이벤트:
            event_입_items.append((product, qty))
        elif product.category == ProductCategory.폐호흡_이벤트:
            event_폐_items.append((product, qty))
        elif product.category in (ProductCategory.입호흡_일반, ProductCategory.폐호흡_일반):
            normal_items.append((product, qty))
        else:
            other_items.append((product, qty))

    result.has_device = has_device
    result.has_high_pod = has_high_pod

    # ── 1. 할인제외 상품: 항상 정가 ──────────────────────────
    for product, qty in excluded_items:
        result.lines.append(LineCalcResult(
            product_id=product.id,
            quantity=qty,
            unit_price=product.normal_price,
            line_total=product.normal_price * qty,
        ))

    # ── 2. 묶음 할인 계산 ────────────────────────────────────
    # 이벤트 + 일반 수량 합산 (할인제외 제외)
    total_입evt = sum(q for _, q in event_입_items)
    total_폐evt = sum(q for _, q in event_폐_items)
    total_normal = sum(q for _, q in normal_items)
    total_event = total_입evt + total_폐evt
    total_bundleable = total_event + total_normal

    # 이벤트 우선 소진으로 3병 묶음 형성
    remaining_event_입 = total_입evt
    remaining_event_폐 = total_폐evt
    remaining_normal = total_normal

    bundle_total = 0
    bundles_3 = 0

    while remaining_event_입 + remaining_event_폐 + remaining_normal >= 3:
        # 이벤트 먼저 소진
        event_in_bundle = min(remaining_event_입 + remaining_event_폐, 3)
        use_입 = min(remaining_event_입, 3)
        use_폐 = min(remaining_event_폐, 3 - use_입)
        event_used = use_입 + use_폐
        normal_in_bundle = min(remaining_normal, 3 - event_used)

        if event_used + normal_in_bundle < 3:
            break

        bundle_price = BUNDLE_3_BASE + (BUNDLE_3_NORMAL * normal_in_bundle)
        bundle_total += bundle_price
        bundles_3 += 1

        remaining_event_입 -= use_입
        remaining_event_폐 -= use_폐
        remaining_normal -= normal_in_bundle

    # 잔여 폐이벤트 2병 묶음
    bundles_2폐 = 0
    while remaining_event_폐 >= 2:
        bundle_total += BUNDLE_2_폐
        remaining_event_폐 -= 2
        bundles_2폐 += 1

    # 잔여 개별 이벤트
    bundle_total += remaining_event_입 * 입이벤트_단가
    bundle_total += remaining_event_폐 * 폐이벤트_단가

    # 잔여 일반 (정가)
    normal_individual_total = 0
    remaining_normal_items = []
    used_normal = total_normal - remaining_normal
    for product, qty in normal_items:
        if used_normal > 0:
            used = min(qty, used_normal)
            used_normal -= used
            remaining_qty = qty - used
        else:
            remaining_qty = qty
        if remaining_qty > 0:
            remaining_normal_items.append((product, remaining_qty))
            normal_individual_total += product.normal_price * remaining_qty

    # 이벤트+묶음일반 라인 생성 (묶음 가격 분배 — 나머지 보정)
    all_event_items = event_입_items + event_폐_items
    bundled_normal_qty_total = total_normal - remaining_normal
    total_bundled = total_event + bundled_normal_qty_total

    if total_bundled > 0:
        distributed = 0
        bundle_line_items = []

        for product, qty in all_event_items:
            if qty > 0:
                bundle_line_items.append((product, qty))

        bundled_normal_remaining = bundled_normal_qty_total
        for product, qty in normal_items:
            bq = min(qty, bundled_normal_remaining)
            if bq > 0:
                bundle_line_items.append((product, bq))
                bundled_normal_remaining -= bq

        for i, (product, qty) in enumerate(bundle_line_items):
            if i < len(bundle_line_items) - 1:
                share = int(bundle_total * qty / total_bundled)
            else:
                share = bundle_total - distributed  # 마지막에 나머지 보정
            distributed += share
            result.lines.append(LineCalcResult(
                product_id=product.id,
                quantity=qty,
                unit_price=share // qty if qty > 0 else 0,
                line_total=share,
            ))

    # 잔여 일반 라인 (정가)
    for product, qty in remaining_normal_items:
        result.lines.append(LineCalcResult(
            product_id=product.id,
            quantity=qty,
            unit_price=product.normal_price,
            line_total=product.normal_price * qty,
        ))

    # 정가 기준 원래 합계
    original_total = (total_입evt * 입이벤트_단가
                      + total_폐evt * 폐이벤트_단가
                      + sum(p.normal_price * q for p, q in normal_items))
    result.event_discount_applied = original_total - (bundle_total + normal_individual_total)

    # ── 3. 기기: 연동할인 적용 ────────────────────────────────
    for product, qty in device_items:
        if product.is_device_linked and product.device_discount_price:
            price = product.safe_device_price
            is_dd = True
        else:
            price = product.normal_price
            is_dd = False
        result.lines.append(LineCalcResult(
            product_id=product.id,
            quantity=qty,
            unit_price=price,
            line_total=price * qty,
            is_device_discount=is_dd,
        ))

    # ── 4. 기타 (코일, 악세사리 등): 정가 ────────────────────
    for product, qty in other_items:
        result.lines.append(LineCalcResult(
            product_id=product.id,
            quantity=qty,
            unit_price=product.normal_price,
            line_total=product.normal_price * qty,
        ))

    result.subtotal = sum(l.line_total for l in result.lines)
    return result


def calc_mileage_earn(total_amount: int, *, eligible: bool = True) -> int:
    """적립금 계산. 결제금액의 1% (10원 단위 절사)."""
    if not eligible or total_amount <= 0:
        return 0
    raw = int(total_amount * 0.01)
    return (raw // 10) * 10


def is_discount_excluded(product: Product) -> bool:
    """할인 제외 상품 여부."""
    return product.category in LIQUID_EXCL


def determine_payment_nature(
    total_amount: int,
    card_amount: int,
    mileage_used: int,
) -> str:
    """결제 성격 자동 판별."""
    if total_amount <= 0 and mileage_used > 0:
        return "마일리지전액"
    if card_amount <= 0:
        return "현금이체"
    if total_amount > 0:
        card_ratio = card_amount / total_amount * 100
        if card_ratio <= 20:
            return "현금이체_카드20이하"
    return "카드"


def determine_earn_eligible(payment_nature: str, has_high_pod: bool) -> bool:
    """적립 가능 여부."""
    if has_high_pod:
        return False
    return payment_nature in ("현금이체", "현금이체_카드20이하")


def determine_service_eligible(payment_nature: str) -> bool:
    """서비스 자격 여부."""
    return payment_nature not in ("카드", "마일리지전액")
