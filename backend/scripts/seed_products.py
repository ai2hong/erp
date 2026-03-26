"""
scripts/seed_products.py — products_master.xlsx 기반 상품 시드

실행:
  cd backend && python3 scripts/seed_products.py

엑셀 구조 (기본자료_정리1 시트):
  Row 1-2: 빈 행
  Row 3-6: 헤더 (병합 셀)
  Row 7+:  데이터
  Col A: 빈 열
  Col B: NO (상품 번호)
  Col C: 구분 (카테고리)
  Col D: 상품명
  Col E: 입고단가
  Col F: 판매단가 — 슬래시 가격 가능 ("50,000 / 55,000")
  Col G: 이벤트할인 적용금액

파싱 규칙:
  1. 기기 슬래시 가격 ("50,000 / 55,000")
     → 앞 = device_discount_price, 뒤 = normal_price
  2. 할인제외 텍스트 ("25,000 (이벤트x)")
     → 숫자만 추출 → normal_price
  3. 카테고리 매핑: XLSX 분류 → ProductCategory enum
  4. 중복(이름+카테고리) → skip
"""

import asyncio
import os
import re
import sys
from typing import Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import openpyxl
except ImportError:
    print("ERROR: openpyxl 이 설치되어 있지 않습니다.")
    print("  pip install openpyxl")
    sys.exit(1)

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.product import Product, ProductCategory, SaleStatus
import app.models  # noqa: F401


# ── 카테고리 매핑 ────────────────────────────────────────────
CATEGORY_MAP = {
    "악세서리": ProductCategory.악세사리,
    "악세사리": ProductCategory.악세사리,
    "입호흡 기기": ProductCategory.입호흡_기기,
    "입호흡 일반": ProductCategory.입호흡_일반,
    "입호흡 이벤트": ProductCategory.입호흡_이벤트,
    "입호흡 코일": ProductCategory.입호흡_코일,
    "입호흡 코일(고가)": ProductCategory.입호흡_코일_고가,
    "입호흡 일반(할인제외)": ProductCategory.입호흡_일반_할인제외,
    "폐호흡 기기": ProductCategory.폐호흡_기기,
    "폐호흡 일반": ProductCategory.폐호흡_일반,
    "폐호흡 이벤트": ProductCategory.폐호흡_이벤트,
    "폐호흡 코일": ProductCategory.폐호흡_코일,
    "폐호흡 코일(고가)": ProductCategory.폐호흡_코일_고가,
    "폐호흡 일반(할인제외)": ProductCategory.폐호흡_일반_할인제외,
    "입호흡 기기(단일가)": ProductCategory.입호흡_기기_단일,
    "입호흡 기기 (단일가)": ProductCategory.입호흡_기기_단일,
    "폐호흡 기기(단일가)": ProductCategory.폐호흡_기기_단일,
    "폐호흡 기기 (단일가)": ProductCategory.폐호흡_기기_단일,
}


def parse_price(value) -> int:
    """문자열/숫자에서 정수 가격 추출. 콤마, 원, 공백 제거."""
    if value is None:
        return 0
    s = str(value).strip()
    if not s or s == "-":
        return 0
    # 숫자와 콤마만 추출
    nums = re.findall(r"[\d,]+", s)
    if not nums:
        return 0
    return int(nums[0].replace(",", ""))


def parse_device_prices(value) -> Tuple[Optional[int], int]:
    """
    기기 슬래시 가격 파싱.
    "50,000 / 55,000" → (50000, 55000)
    일반 가격 → (None, price)
    """
    if value is None:
        return None, 0
    s = str(value).strip()
    if "/" in s:
        parts = s.split("/")
        if len(parts) == 2:
            discount = parse_price(parts[0])
            normal = parse_price(parts[1])
            if discount > 0 and normal > 0:
                return discount, normal
    return None, parse_price(s)


XLSX_PATH = os.path.join(os.path.dirname(__file__), "products_master.xlsx")

# 엑셀 데이터 시작 행 (Row 7, 1-indexed)
DATA_START_ROW = 7

# 컬럼 인덱스 (0-indexed, values_only=True 기준)
COL_NO = 1          # B열: 상품 번호
COL_CATEGORY = 2    # C열: 구분
COL_NAME = 3        # D열: 상품명
COL_COST = 4        # E열: 입고단가
COL_SELL = 5        # F열: 판매단가
COL_EVENT = 6       # G열: 이벤트할인적용금액

# 유효한 카테고리 키워드 (숫자 오인 방지)
VALID_CATEGORY_KEYWORDS = set(CATEGORY_MAP.keys())


def validate_category(raw_cat):
    """카테고리 값이 유효한 문자열인지 검증."""
    if not raw_cat:
        return False
    s = str(raw_cat).strip()
    if not s:
        return False
    # 숫자만으로 이루어진 값은 잘못된 매핑
    if s.isdigit():
        return False
    return True


async def seed_products():
    if not os.path.exists(XLSX_PATH):
        print("ERROR: %s 파일을 찾을 수 없습니다." % XLSX_PATH)
        sys.exit(1)

    wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)
    ws = wb.active

    # 헤더 행 건너뛰고 데이터 행부터 읽기
    rows = list(ws.iter_rows(min_row=DATA_START_ROW, values_only=True))

    total = 0
    inserted = 0
    skipped = 0
    updated = 0
    errors = []

    async with AsyncSessionLocal() as session:
        for i, row in enumerate(rows, start=DATA_START_ROW):
            try:
                if not row or len(row) < COL_SELL + 1:
                    continue

                raw_no = row[COL_NO]
                raw_category = str(row[COL_CATEGORY]).strip() if row[COL_CATEGORY] else ""
                raw_name = str(row[COL_NAME]).strip() if row[COL_NAME] else ""

                if not raw_name or not raw_category:
                    continue

                # 카테고리 유효성 검사
                if not validate_category(raw_category):
                    errors.append(
                        "Row %d: 유효하지 않은 카테고리 '%s' — %s" % (i, raw_category, raw_name)
                    )
                    skipped += 1
                    continue

                total += 1

                category = CATEGORY_MAP.get(raw_category)
                if category is None:
                    errors.append(
                        "Row %d: 알 수 없는 카테고리 '%s' — %s" % (i, raw_category, raw_name)
                    )
                    skipped += 1
                    continue

                # 입고단가
                cost_price = parse_price(row[COL_COST]) if len(row) > COL_COST else 0

                # 판매가 — 슬래시 가격 처리
                sell_raw = row[COL_SELL] if len(row) > COL_SELL else None
                device_discount, normal_price = parse_device_prices(sell_raw)

                # 이벤트할인적용금액
                event_raw = row[COL_EVENT] if len(row) > COL_EVENT else None
                event_price = parse_price(event_raw) if event_raw is not None else 0

                # 이벤트 카테고리: event_price > 0 이면 normal_price로 사용
                if event_price > 0 and "이벤트" in raw_category:
                    normal_price = event_price

                # 기기 분류인데 슬래시가 없으면 단일가 기기로 재분류
                if category in (ProductCategory.입호흡_기기, ProductCategory.폐호흡_기기):
                    if device_discount is None:
                        if category == ProductCategory.입호흡_기기:
                            category = ProductCategory.입호흡_기기_단일
                        else:
                            category = ProductCategory.폐호흡_기기_단일

                # 중복 체크 (이름 + 카테고리): skip 전략
                existing = await session.scalar(
                    select(Product).where(
                        Product.name == raw_name,
                        Product.category == category,
                    )
                )
                if existing:
                    skipped += 1
                    continue

                product = Product(
                    category=category,
                    name=raw_name,
                    normal_price=normal_price,
                    device_discount_price=device_discount,
                    cost_price=cost_price if cost_price > 0 else None,
                    sale_status=SaleStatus.판매중,
                )
                session.add(product)
                inserted += 1

                # 100개마다 진행 상황 출력
                if inserted % 100 == 0:
                    print("  ... %d개 삽입 완료 (Row %d)" % (inserted, i))

            except Exception as e:
                errors.append("Row %d: %s — %s" % (i, e, row[:7] if row else row))
                skipped += 1

        await session.commit()

    print()
    print("=== VAPE DOG ERP Product Seed Result ===")
    print("Total rows processed: %d" % total)
    print("Inserted: %d" % inserted)
    print("Skipped (duplicate): %d" % skipped)
    print("Updated: %d" % updated)
    if errors:
        print("\nErrors (%d):" % len(errors))
        for err in errors:
            print("  - %s" % err)
    print()
    if inserted + skipped == total:
        print("OK: 전체 %d건 중 %d건 삽입, %d건 스킵" % (total, inserted, skipped))
    else:
        print("WARNING: 합계 불일치 — total=%d, inserted+skipped=%d" % (total, inserted + skipped))


if __name__ == "__main__":
    asyncio.run(seed_products())
