"""
scripts/simulate_full.py — 전체 거래 시뮬레이션

일반적인 판매 시나리오를 시뮬레이션하여 가격/서비스/적립금 로직 검증.

실행:
  cd backend && python3 scripts/simulate_full.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.engines.price_engine import (
    calc_cart, calc_mileage_earn,
    determine_payment_nature, determine_earn_eligible, determine_service_eligible,
)
from app.engines.service_engine import calc_services
from app.models.product import ProductCategory, LIQUID_ALL, DEVICE_ALL
from unittest.mock import MagicMock


def make_product(pid, category, normal_price, device_discount_price=None):
    p = MagicMock()
    p.id = pid
    p.category = category
    p.normal_price = normal_price
    p.device_discount_price = device_discount_price
    p.is_liquid = category in LIQUID_ALL
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
    if device_discount_price and 0 < device_discount_price < normal_price:
        p.safe_device_price = device_discount_price
    else:
        p.safe_device_price = normal_price
    return p


def run_scenario(name, products_with_qty, card_amount=0, mileage_used=0, discount=0):
    print("=" * 60)
    print("시나리오: %s" % name)
    print("-" * 60)

    cart = calc_cart(products_with_qty)

    subtotal = cart.subtotal
    total = subtotal - discount - mileage_used
    if total < 0:
        total = 0

    nature = determine_payment_nature(total, card_amount, mileage_used)
    earn_ok = determine_earn_eligible(nature, cart.has_high_pod)
    svc_ok = determine_service_eligible(nature)
    earned = calc_mileage_earn(total, eligible=earn_ok)

    liquid_count = sum(q for p, q in products_with_qty if p.category in LIQUID_ALL)
    device_count = sum(q for p, q in products_with_qty if p.category in DEVICE_ALL)
    svc = calc_services(liquid_count, device_count, service_eligible=svc_ok)

    print("  장바구니:")
    for line in cart.lines:
        print("    - product_id=%d  qty=%d  단가=%s  소계=%s  기기할인=%s"
              % (line.product_id, line.quantity, line.unit_price, line.line_total, line.is_device_discount))
    print("  소계: %s" % subtotal)
    print("  할인: %s" % discount)
    print("  마일리지 사용: %s" % mileage_used)
    print("  결제금액: %s" % total)
    print("  카드금액: %s" % card_amount)
    print("  결제성격: %s" % nature)
    print("  적립가능: %s  적립금: %s" % (earn_ok, earned))
    print("  서비스자격: %s" % svc_ok)
    print("  서비스 항목:")
    if svc.items:
        for item in svc.items:
            print("    - %s x%d (%s)" % (item.service_type, item.quantity, item.note))
    else:
        print("    (없음)")
    print()
    return total


def main():
    print("\n=== VAPE DOG ERP — 전체 거래 시뮬레이션 ===\n")
    passed = 0
    failed = 0

    # 시나리오 1: 기본 3병 묶음 (이체)
    total = run_scenario(
        "기본 3병 묶음 — 입이벤트 3병, 이체",
        [(make_product(1, ProductCategory.입호흡_이벤트, 20000), 3)],
    )
    if total == 50000:
        print("  -> PASS")
        passed += 1
    else:
        print("  -> FAIL (expected 50000, got %s)" % total)
        failed += 1

    # 시나리오 2: 3병 묶음 + 기기 (이체)
    total = run_scenario(
        "3병 묶음 + 기기 연동할인 — 입이벤트 3병 + 입기기 1대",
        [
            (make_product(1, ProductCategory.입호흡_이벤트, 20000), 3),
            (make_product(2, ProductCategory.입호흡_기기, 55000, 50000), 1),
        ],
    )
    if total == 100000:
        print("  -> PASS")
        passed += 1
    else:
        print("  -> FAIL (expected 100000, got %s)" % total)
        failed += 1

    # 시나리오 3: 카드 결제
    total = run_scenario(
        "카드 결제 — 입이벤트 3병, 카드 전액",
        [(make_product(1, ProductCategory.입호흡_이벤트, 20000), 3)],
        card_amount=50000,
    )
    if total == 50000:
        print("  -> PASS (카드 결제, 적립/서비스 불가)")
        passed += 1
    else:
        print("  -> FAIL (expected 50000)")
        failed += 1

    # 시나리오 4: 마일리지 전액
    total = run_scenario(
        "마일리지 전액 — 코일 1개",
        [(make_product(1, ProductCategory.입호흡_코일, 4000), 1)],
        mileage_used=4000,
    )
    if total == 0:
        print("  -> PASS (마일리지 전액, 서비스 불가)")
        passed += 1
    else:
        print("  -> FAIL")
        failed += 1

    # 시나리오 5: 폐이벤트 2병 묶음
    total = run_scenario(
        "폐이벤트 2병 묶음",
        [(make_product(1, ProductCategory.폐호흡_이벤트, 25000), 2)],
    )
    if total == 45000:
        print("  -> PASS")
        passed += 1
    else:
        print("  -> FAIL (expected 45000, got %s)" % total)
        failed += 1

    # 시나리오 6: 할인제외 + 이벤트
    total = run_scenario(
        "할인제외 포함 — 이벤트 3 + 할인제외 1",
        [
            (make_product(1, ProductCategory.입호흡_이벤트, 20000), 3),
            (make_product(2, ProductCategory.입호흡_일반_할인제외, 25000), 1),
        ],
    )
    if total == 75000:
        print("  -> PASS")
        passed += 1
    else:
        print("  -> FAIL (expected 75000, got %s)" % total)
        failed += 1

    # 시나리오 7: 혼합 (이벤트 + 일반) 묶음
    total = run_scenario(
        "혼합 3병 — 입이벤트 2 + 입일반 1",
        [
            (make_product(1, ProductCategory.입호흡_이벤트, 20000), 2),
            (make_product(2, ProductCategory.입호흡_일반, 21500), 1),
        ],
    )
    if total == 55000:
        print("  -> PASS")
        passed += 1
    else:
        print("  -> FAIL (expected 55000, got %s)" % total)
        failed += 1

    # 시나리오 8: 악세사리만
    total = run_scenario(
        "악세사리만 — 배터리 2개",
        [(make_product(1, ProductCategory.악세사리, 15000), 2)],
    )
    if total == 30000:
        print("  -> PASS")
        passed += 1
    else:
        print("  -> FAIL (expected 30000, got %s)" % total)
        failed += 1

    print("=" * 60)
    print("결과: %d PASS / %d FAIL" % (passed, failed))
    if failed == 0:
        print("ALL SCENARIOS PASSED!")
    else:
        print("SOME SCENARIOS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
