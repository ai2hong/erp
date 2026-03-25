import asyncio
import os
import secrets

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.staff import Staff, StaffRole, Store
from app.models.customer import Customer
from app.core.security import hash_password

# 모든 모델을 import해서 테이블 인식
import app.models  # noqa: F401


DEFAULT_OWNER_LOGIN_ID = os.getenv("SEED_OWNER_LOGIN_ID", "owner_admin")
DEFAULT_OWNER_NAME = os.getenv("SEED_OWNER_NAME", "사장")
DEFAULT_OWNER_PASSWORD = (os.getenv("SEED_OWNER_PASSWORD") or secrets.token_hex(16))[:32]

STORES = [
    {"name": "증산점", "address": None, "phone": None},
    {"name": "양산점", "address": None, "phone": None},
    {"name": "범어점", "address": None, "phone": None},
]

SAMPLE_CUSTOMERS = [
    {"name": "김단골", "phone": "010-1234-5678"},
    {"name": "이방문", "phone": "010-2345-6789"},
    {"name": "박신규", "phone": "010-3456-7890"},
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        created_store_names = []

        for store_data in STORES:
            existing_store = await session.scalar(
                select(Store).where(Store.name == store_data["name"])
            )
            if existing_store is None:
                session.add(Store(**store_data))
                created_store_names.append(store_data["name"])

        await session.commit()

        first_store = await session.scalar(select(Store).order_by(Store.id.asc()))
        if first_store is None:
            raise RuntimeError("Store seed failed: no store found after insert")

        existing_owner = await session.scalar(
            select(Staff).where(Staff.login_id == DEFAULT_OWNER_LOGIN_ID)
        )

        created_owner = False
        if existing_owner is None:
            owner = Staff(
                store_id=first_store.id,
                name=DEFAULT_OWNER_NAME,
                login_id=DEFAULT_OWNER_LOGIN_ID,
                hashed_password=hash_password(DEFAULT_OWNER_PASSWORD),
                role=StaffRole.사장,
                is_active=True,
            )
            session.add(owner)
            await session.commit()
            created_owner = True

        # 샘플 고객 시드
        created_customers = []
        for cust_data in SAMPLE_CUSTOMERS:
            existing = await session.scalar(
                select(Customer).where(Customer.phone == cust_data["phone"])
            )
            if existing is None:
                session.add(Customer(**cust_data))
                created_customers.append(cust_data["name"])
        await session.commit()

        print("=== VAPE DOG ERP Seed Result ===")
        print(f"Created stores: {created_store_names if created_store_names else 'none (already exist)'}")
        print(f"Owner login_id: {DEFAULT_OWNER_LOGIN_ID}")
        print(f"Owner created: {'yes' if created_owner else 'no (already exists)'}")
        if created_owner:
            print(f"Temporary owner password: {DEFAULT_OWNER_PASSWORD}")
            print("IMPORTANT: log in once, then change this password immediately.")
        print(f"Created customers: {created_customers if created_customers else 'none (already exist)'}")


if __name__ == '__main__':
    asyncio.run(seed())
