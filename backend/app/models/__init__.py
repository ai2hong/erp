"""
models 패키지 — 전체 모델 import

Alembic과 create_tables()가 모든 테이블을 인식하려면
이 파일에서 모든 모델을 import 해야 합니다.
"""

from app.models.auth import (
    StaffRegistrationRequest, LoginHistory, StaffSession, TokenBlacklist,
)
from app.models.staff import Staff, Store, StaffRole, StaffStoreAccess
from app.models.customer import Customer
from app.models.product import Product, ProductCategory, SaleStatus
from app.models.transaction import Transaction, TxChannel, TxStatus, TxColor, PaymentNature
from app.models.transaction_line import TransactionLine
from app.models.payment import Payment, PaymentMethod
from app.models.mileage_ledger import MileageLedger, MileageType
from app.models.service_record import ServiceRecord
from app.models.unpaid_service import UnpaidService
from app.models.inventory import Inventory
from app.models.inventory_move import InventoryMove, MoveType
from app.models.device_ledger import DeviceLedger
from app.models.reservation import Reservation, ReservationStatus
from app.models.exchange_case import ExchangeCase, ExchangeStatus
from app.models.as_case import AsCase, AsCaseStatus
from app.models.day_close import DayClose, DayCloseStatus
from app.models.staff_attendance import StaffAttendance, AttendanceSummary
from app.models.transaction_correction import TransactionCorrection, CorrectionStatus, CorrectionType

__all__ = [
    "StaffRegistrationRequest", "LoginHistory", "StaffSession", "TokenBlacklist",
    "Staff", "Store", "StaffRole", "StaffStoreAccess",
    "Customer",
    "Product", "ProductCategory", "SaleStatus",
    "Transaction", "TxChannel", "TxStatus", "TxColor", "PaymentNature",
    "TransactionLine",
    "Payment", "PaymentMethod",
    "MileageLedger", "MileageType",
    "ServiceRecord",
    "UnpaidService",
    "Inventory",
    "InventoryMove", "MoveType",
    "DeviceLedger",
    "Reservation", "ReservationStatus",
    "ExchangeCase", "ExchangeStatus",
    "AsCase", "AsCaseStatus",
    "DayClose", "DayCloseStatus",
    "StaffAttendance", "AttendanceSummary",
    "TransactionCorrection", "CorrectionStatus", "CorrectionType",
]
