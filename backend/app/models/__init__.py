# 모든 모델을 여기서 import해 SQLAlchemy 레지스트리에 등록
from app.models.staff import Staff, Store, StaffStoreAccess  # noqa: F401
from app.models.auth import (  # noqa: F401
    StaffRegistrationRequest, StaffSession, TokenBlacklist, LoginHistory
)
from app.models.customer import Customer  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.transaction import Transaction  # noqa: F401
from app.models.transaction_line import TransactionLine  # noqa: F401
from app.models.payment import Payment  # noqa: F401
from app.models.inventory import Inventory  # noqa: F401
from app.models.inventory_move import InventoryMove  # noqa: F401
from app.models.service_record import ServiceRecord  # noqa: F401
from app.models.mileage_ledger import MileageLedger  # noqa: F401
from app.models.store_transfer import StoreTransfer  # noqa: F401
from app.models.day_close import DayClose  # noqa: F401
from app.models.approval_log import ApprovalLog  # noqa: F401
from app.models.reservation import Reservation  # noqa: F401
from app.models.exchange_case import ExchangeCase  # noqa: F401
from app.models.unpaid_service import UnpaidService  # noqa: F401
from app.models.as_case import AsCase  # noqa: F401
from app.models.device_ledger import DeviceLedger  # noqa: F401
