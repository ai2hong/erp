"""
tests/test_service_engine.py — 서비스 자격 판별 엔진 단위 테스트
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.engines.service_engine import calc_services, check_bonus_service, ServiceItem


# ══════════════════════════════════════════════════════════════
# 1. 기본 서비스 규칙
# ══════════════════════════════════════════════════════════════

class TestBasicService:
    """액상 수량별 서비스."""

    def test_1_liquid(self):
        """1병 → 액상서비스 1개."""
        result = calc_services(1, 0, service_eligible=True)
        assert result.eligible is True
        assert len(result.items) == 1
        assert result.items[0].service_type == "액상서비스"
        assert result.items[0].quantity == 1

    def test_2_liquid(self):
        """2병 → 액상서비스 2개."""
        result = calc_services(2, 0, service_eligible=True)
        assert result.eligible is True
        svc = [i for i in result.items if i.service_type == "액상서비스"]
        assert len(svc) == 1
        assert svc[0].quantity == 2

    def test_3_liquid_set3(self):
        """3병 → SET3 묶음 1개."""
        result = calc_services(3, 0, service_eligible=True)
        assert result.eligible is True
        set3 = [i for i in result.items if i.service_type == "SET3"]
        assert len(set3) == 1
        assert set3[0].quantity == 1

    def test_4_liquid(self):
        """4병 → SET3 1개 + 액상서비스 1개."""
        result = calc_services(4, 0, service_eligible=True)
        assert result.eligible is True
        set3 = [i for i in result.items if i.service_type == "SET3"]
        svc = [i for i in result.items if i.service_type == "액상서비스"]
        assert set3[0].quantity == 1
        assert svc[0].quantity == 1

    def test_6_liquid(self):
        """6병 → SET3 2개."""
        result = calc_services(6, 0, service_eligible=True)
        set3 = [i for i in result.items if i.service_type == "SET3"]
        assert set3[0].quantity == 2

    def test_7_liquid(self):
        """7병 → SET3 2개 + 액상서비스 1개."""
        result = calc_services(7, 0, service_eligible=True)
        set3 = [i for i in result.items if i.service_type == "SET3"]
        svc = [i for i in result.items if i.service_type == "액상서비스"]
        assert set3[0].quantity == 2
        assert svc[0].quantity == 1


class TestDeviceService:
    """기기 구매 서비스."""

    def test_device_only(self):
        """기기만 → 기기증정 1개."""
        result = calc_services(0, 1, service_eligible=True)
        assert result.eligible is True
        gift = [i for i in result.items if i.service_type == "기기증정"]
        assert len(gift) == 1
        assert gift[0].quantity == 1

    def test_device_2(self):
        """기기 2대 → 기기증정 2개."""
        result = calc_services(0, 2, service_eligible=True)
        gift = [i for i in result.items if i.service_type == "기기증정"]
        assert gift[0].quantity == 2

    def test_device_plus_liquid(self):
        """기기 1 + 액상 3 → 기기증정 1 + SET3 1."""
        result = calc_services(3, 1, service_eligible=True)
        assert result.eligible is True
        gift = [i for i in result.items if i.service_type == "기기증정"]
        set3 = [i for i in result.items if i.service_type == "SET3"]
        assert gift[0].quantity == 1
        assert set3[0].quantity == 1


# ══════════════════════════════════════════════════════════════
# 2. 서비스 불가 거래
# ══════════════════════════════════════════════════════════════

class TestServiceIneligible:
    """서비스 불가."""

    def test_not_eligible(self):
        """서비스 자격 없으면 항상 빈 결과."""
        result = calc_services(3, 1, service_eligible=False)
        assert result.eligible is False
        assert len(result.items) == 0

    def test_no_items(self):
        """상품 0개."""
        result = calc_services(0, 0, service_eligible=True)
        assert result.eligible is False


# ══════════════════════════════════════════════════════════════
# 3. 단골 보너스 서비스
# ══════════════════════════════════════════════════════════════

class TestBonusService:
    """단골 추가 서비스."""

    def test_qualifies(self):
        """10회 방문 + 50만원 이상 → 대상."""
        result = check_bonus_service(10, 500000)
        assert result is not None

    def test_visit_not_enough(self):
        """9회 → 미대상."""
        result = check_bonus_service(9, 500000)
        assert result is None

    def test_purchase_not_enough(self):
        """50만원 미만 → 미대상."""
        result = check_bonus_service(10, 499999)
        assert result is None

    def test_both_not_enough(self):
        result = check_bonus_service(5, 200000)
        assert result is None


# ══════════════════════════════════════════════════════════════
# 4. AMBIGUOUS 경계
# ══════════════════════════════════════════════════════════════

class TestAmbiguousBoundary:
    """
    AMBIGUOUS — 기준서에 명확히 기술되지 않은 경계.
    """

    def test_exactly_10_visits_500k(self):
        """AMBIGUOUS: 정확히 10회/50만원 → 현재 구현은 대상."""
        assert check_bonus_service(10, 500000) is not None

    def test_large_liquid_count(self):
        """AMBIGUOUS: 대량 100병 → SET3 33개 + 액상서비스 1개."""
        result = calc_services(100, 0, service_eligible=True)
        set3 = [i for i in result.items if i.service_type == "SET3"]
        svc = [i for i in result.items if i.service_type == "액상서비스"]
        assert set3[0].quantity == 33
        assert svc[0].quantity == 1
        assert result.total_count == 34
