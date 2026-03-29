"""
VapeERP 매장 + 관리자 초기 데이터

실행 순서:
  1. python seed_stores_staff.py
  2. python seed_products.py

매장 추가: STORES 리스트에 항목만 추가
"""
import sys, os, asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import AsyncSessionLocal
from app.models.staff import Store, Staff, StaffRole
from app.core.security import hash_password
from sqlalchemy import select

STORES = [
    {'name': '증산점', 'address': '부산시 북구 증산로 ...',   'phone': '051-000-0001'},
    {'name': '양산점', 'address': '경남 양산시 ...',          'phone': '055-000-0001'},
    {'name': '범어점', 'address': '대구시 수성구 범어동 ...', 'phone': '053-000-0001'},
    {'name': '서면점', 'address': '부산시 부산진구 서면 ...', 'phone': '051-000-0002'},
]

ADMIN = {
    'name':     '관리자',
    'login_id': 'admin',
    'password': 'vapedog1234',   # ← 운영 전 반드시 변경
    'role':     StaffRole.관리자,
    'store_id': 1,
}


async def main():
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(Store))
            if result.scalars().first():
                print("매장이 이미 있습니다. 건너뜁니다.")
            else:
                for s in STORES:
                    db.add(Store(name=s['name'], address=s['address'],
                                 phone=s['phone'], is_active=True))
                await db.flush()
                result = await db.execute(select(Store).order_by(Store.id))
                stores = result.scalars().all()
                print(f"✓ 매장 {len(stores)}개 생성:")
                for s in stores:
                    print(f"  store_id={s.id} {s.name}")

            result = await db.execute(
                select(Staff).where(Staff.login_id == ADMIN['login_id'])
            )
            if result.scalar_one_or_none():
                print("\n관리자 계정 이미 있습니다.")
            else:
                db.add(Staff(
                    name=ADMIN['name'],
                    login_id=ADMIN['login_id'],
                    hashed_password=hash_password(ADMIN['password']),
                    role=ADMIN['role'],
                    store_id=ADMIN['store_id'],
                    is_active=True,
                ))
                print(f"\n✓ 관리자 계정: {ADMIN['login_id']} / {ADMIN['password']}")
                print("  ※ 운영 전 반드시 비밀번호를 변경하세요!")

            await db.commit()
            print("\n완료!")

        except Exception as e:
            await db.rollback()
            print(f"오류: {e}")
            raise


if __name__ == '__main__':
    asyncio.run(main())
