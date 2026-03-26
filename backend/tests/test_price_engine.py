"""
tests/test_price_engine.py — 가격 계산 엔진 단위 테스트

기준서 v8 규칙 기반 테스트 케이스.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock
from app.engines.price_engine import (
    calc_cart,
    calc_mileage_earn,
    determine_payment_nature,
    determine_earn_eligible,
    determine_service_eligible,
    get_unit_price,
    BUNDLE_3_BASE,
    BUNDLE_3_NORMAL,
    BUNDLE_2_폐,
)
from app.models.product import ProductCategory


# ── 헬퍼: mock Product 생성 ─────────────────────────────────

def make_product(
    pid=1,
    category=ProductCategory.입호흡_이벤트,
    normal_price=20000,
    device_discount_price=None,
):
    p = MagicMock()
    p.id = pid
    p.category = category
    p.normal_price = normal_price
    p.device_discount_price = device_discount_price
    p.is_liquid = category in {
        ProductCategory.입호흡_이벤트, ProductCategory.입호흡_일반,
        ProductCategory.입호흡_일반_할인제외, ProductCategory.폐호흡_이벤트,
        ProductCategory.폐호흡_일반, ProductCategory.폐호흡_일반_할인제외,
    }
    p.is_excluded = category in {
        ProductCategory.입호흡_일반_할인제외, ProductCategory.폐호흡_일반_할인제외,
    }
    p.is_device = category in {
        ProductCategory.입호흡_기기, ProductCategory.폐호흡_기기,
        ProductCategory.입호흡_기기_단일, ProductCategory.폐호흡_기기_단일,
    }
    p.is_device_linked = category in {
        ProductCategory.입호흡_기기, ProductCategory.폐호흡_기기,
    }
    p.is_device_fixed = category in {
        ProductCategory.입호흡_기기_단일, ProductCategory.폐호흡_기기_단일,
    }
    p.is_high_pod = category in {
        ProductCategory.입호흡_코일_고가, ProductCategory.폐호흡_코일_고가,
    }
    # safe_device_price
    if device_discount_price and 0 < device_discount_price < normal_price:
        p.safe_device_price = device_discount_price
    else:
        p.safe_device_price = normal_price
    return p


# ══════════════════════════════════════════════════════════════
# 1. 묶음 할인 테스트
# ══════════════════════════════════════════════════════════════

class TestBundle3:
    """3병 묶음 할인."""

    def test_3_event_입(self):
        """입이벤트 3병 → 50,000."""
        items = [(make_product(i, ProductCategory.입호흡_이벤트, 20000), 1) for i in range(3)]
        cart = calc_cart(items)
        assert cart.subtotal == BUNDLE_3_BASE  # 50,000

    def test_3_event_폐(self):
        """폐이벤트 3병 → 50,000."""
        items = [(make_product(i, ProductCategory.폐호흡_이벤트, 25000), 1) for i in range(3)]
        cart = calc_cart(items)
        assert cart.subtotal == BUNDLE_3_BASE  # 50,000

    def test_3_event_mixed(self):
        """입이벤트 2 + 폐이벤트 1 → 50,000."""
        items = [
            (make_product(1, ProductCategory.입호흡_이벤트, 20000), 2),
            (make_product(2, ProductCategory.폐호흡_이벤트, 25000), 1),
        ]
        cart = calc_cart(items)
        assert cart.subtotal == BUNDLE_3_BASE

    def test_2_event_1_normal(self):
        """이벤트 2 + 일반 1 → 50,000 + 5,000 = 55,000."""
        items = [
            (make_product(1, ProductCategory.입호흡_이벤트, 20000), 2),
            (make_product(2, ProductCategory.입호흡_일반, 21500), 1),
        ]
        cart = calc_cart(items)
        assert cart.subtotal == BUNDLE_3_BASE + BUNDLE_3_NORMAL * 1  # 55,000

    def test_1_event_2_normal(self):
        """이벤트 1 + 일반 2 → 50,000 + 5,000 * 2 = 60,000."""
        items = [
            (make_product(1, ProductCategory.입호흡_이벤트, 20000), 1),
            (make_product(2, ProductCategory.입호흡_일반, 21500), 2),
        ]
        cart = calc_cart(items)
        assert cart.subtotal == BUNDLE_3_BASE + BUNDLE_3_NORMAL * 2  # 60,000

    def test_6_event(self):
        """이벤트 6병 → 2 묶음 = 100,000."""
        items = [(make_product(1, ProductCategory.입호흡_이벤트, 20000), 6)]
        cart = calc_cart(items)
        assert cart.subtotal == BUNDLE_3_BASE * 2

    def test_qty_via_tuple(self):
        """하나의 상품 qty=3."""
        p = make_product(1, ProductCategory.입호흡_이벤트, 20000)
        cart = calc_cart([(p, 3)])
        assert cart.subtotal == BUNDLE_3_BASE


class TestBundle2폐:
    """폐이벤트 2병 묶음 (3병 이후 잔여)."""

    def test_2_폐event(self):
        """폐이벤트 2병 → 45,000."""
        items = [(make_product(1, ProductCategory.폐호흡_이벤트, 25000), 2)]
        cart = calc_cart(items)
        assert cart.subtotal == BUNDLE_2_폐  # 45,000

    def test_5_폐event(self):
        """폐이벤트 5병 → 3묶음(50,000) + 2묶음(45,000) = 95,000."""
        items = [(make_product(1, ProductCategory.폐호흡_이벤트, 25000), 5)]
        cart = calc_cart(items)
        assert cart.subtotal == BUNDLE_3_BASE + BUNDLE_2_폐

    def test_1_폐event_no_bundle(self):
        """폐이벤트 1병 → 25,000 (단품)."""
        items = [(make_product(1, ProductCategory.폐호흡_이벤트, 25000), 1)]
        cart = calc_cart(items)
        assert cart.subtotal == 25000


class TestExcluded:
    """할인제외 상품은 항상 정가."""

    def test_excluded_alone(self):
        """할인제외 1병 → 정가."""
        p = make_product(1, ProductCategory.입호흡_일반_할인제외, 25000)
        cart = calc_cart([(p, 1)])
        assert cart.subtotal == 25000

    def test_excluded_not_in_bundle(self):
        """이벤트 2 + 할인제외 1 → 묶음 안됨, 개별 정가."""
        items = [
            (make_product(1, ProductCategory.입호흡_이벤트, 20000), 2),
            (make_product(2, ProductCategory.입호흡_일반_할인제외, 25000), 1),
        ]
        cart = calc_cart(items)
        # 이벤트 2병 = 개별 40,000 + 할인제외 25,000 = 65,000
        assert cart.subtotal == 20000 * 2 + 25000

    def test_3_event_plus_excluded(self):
        """이벤트 3 + 할인제외 1 → 묶음 50,000 + 할인제외 25,000."""
        items = [
            (make_product(1, ProductCategory.입호흡_이벤트, 20000), 3),
            (make_product(2, ProductCategory.입호흡_일반_할인제외, 25000), 1),
        ]
        cart = calc_cart(items)
        assert cart.subtotal == BUNDLE_3_BASE + 25000


# ══════════════════════════════════════════════════════════════
# 2. 기기 연동 할인
# ══════════════════════════════════════════════════════════════

class TestDeviceDiscount:
    """기기 연동 할인."""

    def test_device_linked(self):
        """연동 기기 → device_discount_price 적용."""
        p = make_product(1, ProductCategory.입호흡_기기, 55000, device_discount_price=50000)
        cart = calc_cart([(p, 1)])
        assert cart.subtotal == 50000
        assert cart.lines[0].is_device_discount is True

    def test_device_fixed(self):
        """단일가 기기 → 정가."""
        p = make_product(1, ProductCategory.입호흡_기기_단일, 55000)
        cart = calc_cart([(p, 1)])
        assert cart.subtotal == 55000
        assert cart.lines[0].is_device_discount is False

    def test_has_device_flag(self):
        """기기 포함 시 has_device = True."""
        p = make_product(1, ProductCategory.입호흡_기기, 55000, device_discount_price=50000)
        cart = calc_cart([(p, 1)])
        assert cart.has_device is True


# ══════════════════════════════════════════════════════════════
# 3. 적립금 계산
# ══════════════════════════════════════════════════════════════

class TestMileageEarn:
    """적립금 = 결제금액의 1% (10원 단위 절사)."""

    def test_basic(self):
        assert calc_mileage_earn(50000) == 500

    def test_10won_round_down(self):
        assert calc_mileage_earn(55000) == 550

    def test_rounding(self):
        """21500 * 0.01 = 215 → 210 (10원 절사)."""
        assert calc_mileage_earn(21500) == 210

    def test_zero(self):
        assert calc_mileage_earn(0) == 0

    def test_not_eligible(self):
        assert calc_mileage_earn(50000, eligible=False) == 0

    def test_negative(self):
        assert calc_mileage_earn(-1000) == 0


# ══════════════════════════════════════════════════════════════
# 4. 결제 성격 판별
# ══════════════════════════════════════════════════════════════

class TestPaymentNature:
    """결제 성격 자동 판별."""

    def test_cash_only(self):
        assert determine_payment_nature(50000, 0, 0) == "현금이체"

    def test_card_only(self):
        assert determine_payment_nature(50000, 50000, 0) == "카드"

    def test_card_20pct(self):
        """카드 20% 이하 → 현금이체_카드20이하."""
        assert determine_payment_nature(100000, 20000, 0) == "현금이체_카드20이하"

    def test_card_21pct(self):
        """카드 21% → 카드."""
        assert determine_payment_nature(100000, 21000, 0) == "카드"

    def test_mileage_full(self):
        """전액 마일리지."""
        assert determine_payment_nature(0, 0, 50000) == "마일리지전액"


class TestEarnEligible:
    """적립 가능 여부."""

    def test_cash_eligible(self):
        assert determine_earn_eligible("현금이체", False) is True

    def test_card_not_eligible(self):
        assert determine_earn_eligible("카드", False) is False

    def test_high_pod_not_eligible(self):
        assert determine_earn_eligible("현금이체", True) is False

    def test_card20_eligible(self):
        assert determine_earn_eligible("현금이체_카드20이하", False) is True


class TestServiceEligible:
    """서비스 자격 여부."""

    def test_cash_eligible(self):
        assert determine_service_eligible("현금이체") is True

    def test_card_not_eligible(self):
        assert determine_service_eligible("카드") is False

    def test_mileage_not_eligible(self):
        assert determine_service_eligible("마일리지전액") is False

    def test_card20_eligible(self):
        assert determine_service_eligible("현금이체_카드20이하") is True


# ══════════════════════════════════════════════════════════════
# 5. 복합 시나리오
# ══════════════════════════════════════════════════════════════

class TestComplexScenarios:
    """실전 복합 시나리오."""

    def test_3event_plus_device(self):
        """이벤트 3 + 기기 1 → 묶음 50,000 + 기기 할인가."""
        items = [
            (make_product(1, ProductCategory.입호흡_이벤트, 20000), 3),
            (make_product(2, ProductCategory.입호흡_기기, 55000, device_discount_price=50000), 1),
        ]
        cart = calc_cart(items)
        assert cart.subtotal == BUNDLE_3_BASE + 50000

    def test_coil_at_normal_price(self):
        """코일 → 정가."""
        p = make_product(1, ProductCategory.입호흡_코일, 4000)
        cart = calc_cart([(p, 2)])
        assert cart.subtotal == 8000

    def test_accessory_at_normal_price(self):
        """악세사리 → 정가."""
        p = make_product(1, ProductCategory.악세사리, 15000)
        cart = calc_cart([(p, 1)])
        assert cart.subtotal == 15000

    def test_high_pod_flag(self):
        """고가 코일 → has_high_pod = True."""
        p = make_product(1, ProductCategory.입호흡_코일_고가, 8000)
        cart = calc_cart([(p, 1)])
        assert cart.has_high_pod is True

    def test_empty_cart(self):
        """빈 장바구니."""
        cart = calc_cart([])
        assert cart.subtotal == 0
        assert cart.lines == []


# ══════════════════════════════════════════════════════════════
# 6. AMBIGUOUS 경계 케이스
# ══════════════════════════════════════════════════════════════

class TestAmbiguousBoundary:
    """
    AMBIGUOUS — 기준서에 명확히 기술되지 않은 경계.
    현재 구현 기준으로 테스트하되, 추후 정책 확인 필요.
    """

    def test_card_exactly_20pct(self):
        """AMBIGUOUS: 카드 정확히 20% → 현금이체_카드20이하 (<=20)."""
        result = determine_payment_nature(100000, 20000, 0)
        assert result == "현금이체_카드20이하"

    def test_normal_3_no_event(self):
        """AMBIGUOUS: 일반 액상만 3병 → 묶음 50,000 + 일반추가 5,000*3 = 65,000."""
        items = [(make_product(1, ProductCategory.입호흡_일반, 21500), 3)]
        cart = calc_cart(items)
        assert cart.subtotal == BUNDLE_3_BASE + BUNDLE_3_NORMAL * 3  # 65,000

    def test_4_event_remainder(self):
        """AMBIGUOUS: 이벤트 4병 → 묶음 50,000 + 잔여 1병 20,000 = 70,000."""
        items = [(make_product(1, ProductCategory.입호흡_이벤트, 20000), 4)]
        cart = calc_cart(items)
        assert cart.subtotal == BUNDLE_3_BASE + 20000

    def test_device_discount_gte_normal(self):
        """AMBIGUOUS: device_discount_price >= normal_price → 정가 사용."""
        p = make_product(1, ProductCategory.입호흡_기기, 50000, device_discount_price=55000)
        cart = calc_cart([(p, 1)])
        # safe_device_price returns normal_price when discount >= normal
        assert cart.subtotal == 50000
