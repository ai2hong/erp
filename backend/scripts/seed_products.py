"""
scripts/seed_products.py — products_master.xlsx 기반 상품 시드

실행:
  cd backend && python3 scripts/seed_products.py

파싱 규칙:
  1. 기기 슬래시 가격 ("50,000 / 55,000")
     → 앞 = device_discount_price, 뒤 = normal_price
  2. 할인제외 텍스트 ("25,000 (이벤트x)")
     → 숫자만 추출 → normal_price
  3. 카테고리 매핑: XLSX 분류 → ProductCategory enum
"""

import asyncio
import os
import re
import sys

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


def parse_device_prices(value) -> tuple[int | None, int]:
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


async def seed_products():
    if not os.path.exists(XLSX_PATH):
        print(f"ERROR: {XLSX_PATH} 파일을 찾을 수 없습니다.")
        sys.exit(1)

    wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(min_row=2, values_only=True))  # 헤더 제외

    total = 0
    inserted = 0
    skipped = 0
    errors = []

    async with AsyncSessionLocal() as session:
        for i, row in enumerate(rows, start=2):
            try:
                if not row or len(row) < 3:
                    continue

                # 컬럼: no / category / name / cost_price / sell_price / event_price
                raw_no = row[0]
                raw_category = str(row[1]).strip() if row[1] else ""
                raw_name = str(row[2]).strip() if row[2] else ""

                if not raw_name or not raw_category:
                    continue

                total += 1

                category = CATEGORY_MAP.get(raw_category)
                if category is None:
                    errors.append(f"Row {i}: 알 수 없는 카테고리 '{raw_category}' — {raw_name}")
                    skipped += 1
                    continue

                # 원가
                cost_price = parse_price(row[3]) if len(row) > 3 else 0

                # 판매가 (sell_price 컬럼)
                sell_raw = row[4] if len(row) > 4 else None
                device_discount, normal_price = parse_device_prices(sell_raw)

                # 이벤트가 (event_price 컬럼) — 있으면 normal_price로 사용
                event_raw = row[5] if len(row) > 5 else None
                if event_raw:
                    event_price = parse_price(event_raw)
                    if event_price > 0 and "이벤트" in raw_category:
                        normal_price = event_price

                # 기기 분류인데 슬래시가 없으면 단일가 기기로 재분류
                if category in (ProductCategory.입호흡_기기, ProductCategory.폐호흡_기기):
                    if device_discount is None:
                        if category == ProductCategory.입호흡_기기:
                            category = ProductCategory.입호흡_기기_단일
                        else:
                            category = ProductCategory.폐호흡_기기_단일

                # 중복 체크
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

            except Exception as e:
                errors.append(f"Row {i}: {e} — {row}")
                skipped += 1

        await session.commit()

    print("=== VAPE DOG ERP Product Seed Result ===")
    print(f"Total rows processed: {total}")
    print(f"Inserted: {inserted}")
    print(f"Skipped (duplicate/error): {skipped}")
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for err in errors:
            print(f"  - {err}")


if __name__ == "__main__":
    asyncio.run(seed_products())
