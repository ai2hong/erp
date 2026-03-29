"""
VapeERP FastAPI 메인 앱
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 모든 모델을 먼저 import — SQLAlchemy 관계 해석에 필요
import app.models.staff
import app.models.auth_models  # auth.py가 이를 재익스포트
import app.models.product
import app.models.inventory
import app.models.inventory_move
import app.models.transaction
import app.models.transaction_line
import app.models.payment
import app.models.customer
import app.models.mileage_ledger
import app.models.device_ledger
import app.models.reservation
import app.models.as_case
import app.models.exchange_case
import app.models.unpaid_service
import app.models.service_record
import app.models.day_close
import app.models.approval_log
import app.models.store_transfer

from app.routers import products, transactions, customers, inventory, auth, transfers

app = FastAPI(title="VapeERP API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(products.router,   prefix="/products",   tags=["상품"])
app.include_router(transactions.router, prefix="/transactions", tags=["거래"])
app.include_router(customers.router,  prefix="/customers",  tags=["고객"])
app.include_router(inventory.router,  prefix="/inventory",  tags=["재고"])
app.include_router(transfers.router,  prefix="/transfers",  tags=["택배/배달"])


@app.get("/")
def root():
    return {"status": "ok", "app": "VapeERP API"}
