"""
VapeERP 상품 시드 데이터
품목.xlsx 기반 — 1,778개 상품

실행 방법:
  cd backend
  python seed_products.py
"""
import pandas as pd
import sys, os, asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import AsyncSessionLocal
import app.models  # 모든 모델을 SQLAlchemy 레지스트리에 등록  # noqa: F401
from app.models.product import Product, ProductCategory, SaleStatus
from sqlalchemy import select

CAT_MAP = {
    '입호흡 이벤트':        ProductCategory.입호흡_이벤트,
    '입호흡 일반':          ProductCategory.입호흡_일반,
    '입호흡 일반(할인제외)': ProductCategory.입호흡_일반_할인제외,
    '폐호흡 이벤트':        ProductCategory.폐호흡_이벤트,
    '폐호흡 일반':          ProductCategory.폐호흡_일반,
    '폐호흡 일반(할인제외)': ProductCategory.폐호흡_일반_할인제외,
    '입호흡 기기':          ProductCategory.입호흡_기기,
    '폐호흡 기기':          ProductCategory.폐호흡_기기,
    '입호흡 코일':          ProductCategory.입호흡_코일,
    '입호흡 코일(고가)':    ProductCategory.입호흡_코일_고가,
    '폐호흡 코일':          ProductCategory.폐호흡_코일,
    '폐호흡 코일(고가)':    ProductCategory.폐호흡_코일_고가,
    '악세서리':             ProductCategory.악세사리,
}


async def main():
    excel_path = os.path.join(os.path.dirname(__file__), '품목.xlsx')
    df = pd.read_excel(excel_path, sheet_name='기본자료_정리1', header=None)

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(Product))
            if result.scalars().first():
                print("이미 상품이 있습니다. 건너뜁니다.")
                return

            products = []
            for i in range(5, len(df)):
                row = df.iloc[i]
                no = row[1]; cat = row[2]; name = row[3]; price = row[5]
                if str(no) == 'nan' or str(name) == 'nan':
                    continue
                db_cat = CAT_MAP.get(str(cat).strip())
                if not db_cat:
                    continue
                try:
                    normal_price = int(float(str(price).replace(',', '')))
                except:
                    normal_price = 0
                products.append(Product(
                    category=db_cat,
                    name=str(name).strip(),
                    normal_price=normal_price,
                    sale_status=SaleStatus.판매중,
                ))

            for p in products:
                db.add(p)
            await db.commit()

            print(f"✓ {len(products)}개 상품 저장 완료!")
            from collections import Counter
            for k, v in sorted(Counter(str(p.category) for p in products).items()):
                print(f"  {k}: {v}개")

        except Exception as e:
            await db.rollback()
            print(f"오류: {e}")
            raise


if __name__ == '__main__':
    asyncio.run(main())
