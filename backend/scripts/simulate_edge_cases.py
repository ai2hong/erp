"""
scripts/simulate_edge_cases.py — 경계 케이스 시뮬레이션

정상 시나리오가 아닌 경계 조건, 예외 상황을 검증.

실행:
  cd backend && python3 scripts/simulate_edge_cases.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.engines.price_engine import (
    calc_cart, calc_mileage_earn,
    determine_payment_nature, determine_earn_eligible, determine_service_eligible,
)
from app.engines.service_engine import calc_services, check_bonus_service
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


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    suffix = " — %s" % detail if detail else ""
    print("  [%s] %s%s" % (status, name, suffix))
    return condition


def main():
    print("\n=== VAPE DOG ERP — Edge Case Simulation ===\n")
    passed = 0
    failed = 0

    # ── 1. 빈 장바구니 ─────────────────────────────────────────
    print("[경계 1] 빈 장바구니")
    cart = calc_cart([])
    if check("subtotal == 0", cart.subtotal == 0):
        passed += 1
    else:
        failed += 1
    if check("lines 비어있음", len(cart.lines) == 0):
        passed += 1
    else:
        failed += 1

    # ── 2. 단일 이벤트 1병 ─────────────────────────────────────
    print("\n[경계 2] 이벤트 1병 (묶음 불가)")
    cart = calc_cart([(make_product(1, ProductCategory.입호흡_이벤트, 20000), 1)])
    if check("subtotal == 20000", cart.subtotal == 20000, "단품 정가"):
        passed += 1
    else:
        failed += 1

    # ── 3. 이벤트 2병 (입호흡, 묶음 불가) ──────────────────────
    print("\n[경계 3] 입이벤트 2병 (3병 묶음 불가)")
    cart = calc_cart([(make_product(1, ProductCategory.입호흡_이벤트, 20000), 2)])
    if check("subtotal == 40000", cart.subtotal == 40000, "2 x 20,000"):
        passed += 1
    else:
        failed += 1

    # ── 4. 폐이벤트 1병 (2병 묶음 불가) ──────────────────────
    print("\n[경계 4] 폐이벤트 1병")
    cart = calc_cart([(make_product(1, ProductCategory.폐호흡_이벤트, 25000), 1)])
    if check("subtotal == 25000", cart.subtotal == 25000):
        passed += 1
    else:
        failed += 1

    # ── 5. 폐이벤트 4병 → 3묶음 + 1잔여 ────────────────────
    print("\n[경계 5] 폐이벤트 4병")
    cart = calc_cart([(make_product(1, ProductCategory.폐호흡_이벤트, 25000), 4)])
    expected = 50000 + 25000  # 3묶음 + 1잔여
    if check("subtotal == %d" % expected, cart.subtotal == expected, "3묶음(50k) + 잔여 1(25k)"):
        passed += 1
    else:
        failed += 1
        print("    actual: %d" % cart.subtotal)

    # ── 6. 기기 할인가 = 정가 → 정가 사용 ─────────────────────
    print("\n[경계 6] 기기 discount_price == normal_price")
    p = make_product(1, ProductCategory.입호흡_기기, 55000, 55000)
    cart = calc_cart([(p, 1)])
    if check("subtotal == 55000", cart.subtotal == 55000, "할인가 = 정가 → 정가"):
        passed += 1
    else:
        failed += 1

    # ── 7. 기기 할인가 None → 정가 ────────────────────────────
    print("\n[경계 7] 기기 discount_price = None")
    p = make_product(1, ProductCategory.입호흡_기기, 55000, None)
    cart = calc_cart([(p, 1)])
    if check("subtotal == 55000", cart.subtotal == 55000):
        passed += 1
    else:
        failed += 1

    # ── 8. 고가 코일 → 적립 불가 ────────────────────────────
    print("\n[경계 8] 고가 코일 → 적립 불가")
    if check("earn not eligible", determine_earn_eligible("현금이체", True) is False):
        passed += 1
    else:
        failed += 1

    # ── 9. 적립금 절사 경계 ──────────────────────────────────
    print("\n[경계 9] 적립금 10원 절사")
    if check("99원 → 0", calc_mileage_earn(99) == 0):
        passed += 1
    else:
        failed += 1
    if check("1000원 → 10", calc_mileage_earn(1000) == 10):
        passed += 1
    else:
        failed += 1
    if check("1999원 → 10", calc_mileage_earn(1999) == 10, "19.99 → 10"):
        passed += 1
    else:
        failed += 1

    # ── 10. 카드 비율 경계 (20% 정확히) ──────────────────────
    print("\n[경계 10] 카드 비율 경계")
    if check("20% → 현금이체_카드20이하", determine_payment_nature(100000, 20000, 0) == "현금이체_카드20이하"):
        passed += 1
    else:
        failed += 1
    if check("20.01% → 카드", determine_payment_nature(100000, 20001, 0) == "카드"):
        passed += 1
    else:
        failed += 1

    # ── 11. 대량 묶음 ──────────────────────────────────────
    print("\n[경계 11] 대량 — 이벤트 100병")
    cart = calc_cart([(make_product(1, ProductCategory.입호흡_이벤트, 20000), 100)])
    expected = 50000 * 33 + 20000 * 1  # 33묶음 + 잔여 1병
    if check("subtotal == %d" % expected, cart.subtotal == expected, "33묶음 + 1잔여"):
        passed += 1
    else:
        failed += 1
        print("    actual: %d" % cart.subtotal)

    # ── 12. 서비스 0건 ──────────────────────────────────────
    print("\n[경계 12] 서비스 대상 없음 (악세사리만)")
    svc = calc_services(0, 0, service_eligible=True)
    if check("eligible == False", svc.eligible is False, "악세사리는 서비스 대상 아님"):
        passed += 1
    else:
        failed += 1

    # ── 13. 단골 경계 ──────────────────────────────────────
    print("\n[경계 13] 단골 서비스 경계")
    if check("9회/50만 → None", check_bonus_service(9, 500000) is None):
        passed += 1
    else:
        failed += 1
    if check("10회/49만9999 → None", check_bonus_service(10, 499999) is None):
        passed += 1
    else:
        failed += 1
    if check("10회/50만 → 대상", check_bonus_service(10, 500000) is not None):
        passed += 1
    else:
        failed += 1

    # ── AMBIGUOUS 케이스 ──────────────────────────────────
    print("\n[AMBIGUOUS] 정책 불명확 경계")

    # 입이벤트 2 + 폐이벤트 1: 혼합 묶음?
    cart = calc_cart([
        (make_product(1, ProductCategory.입호흡_이벤트, 20000), 2),
        (make_product(2, ProductCategory.폐호흡_이벤트, 25000), 1),
    ])
    check("AMBIGUOUS: 입2+폐1 혼합묶음", cart.subtotal == 50000, "현재 구현: 이벤트 혼합 묶음 50,000")

    # 일반 액상만 3병 묶음: 50k + 5k*3?
    cart = calc_cart([(make_product(1, ProductCategory.입호흡_일반, 21500), 3)])
    check("AMBIGUOUS: 일반3병 묶음", cart.subtotal == 65000, "현재 구현: 50k + 5k*3 = 65k")

    # 할인 > 결제금
    nature = determine_payment_nature(-5000, 0, 0)
    check("AMBIGUOUS: 음수 결제금", nature == "현금이체", "할인 초과 시 결제성격")

    print("\n" + "=" * 60)
    print("결과: %d PASS / %d FAIL" % (passed, failed))
    if failed == 0:
        print("ALL EDGE CASES PASSED!")
    else:
        print("SOME EDGE CASES FAILED — 위 FAIL 항목 확인")
        sys.exit(1)


if __name__ == "__main__":
    main()
