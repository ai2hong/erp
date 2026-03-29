"""
거래 헤더 모델 v2
- TxColor: VIP 제거 → 할인으로 교체
- 핑크색 = 할인 적용 거래 (기존 VIP 색상 재활용)
- discount_amount, discount_reason 컬럼 추가
"""
from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, Text, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class TxChannel(str, enum.Enum):
    매장 = "매장"
    배달 = "배달"
    택배 = "택배"


class TxStatus(str, enum.Enum):
    임시저장 = "임시저장"
    완료     = "완료"
    부분환불 = "부분환불"
    전체취소 = "전체취소"
    정정완료 = "정정완료"


class TxColor(str, enum.Enum):
    """
    거래 색상 분류 (관리자 뷰)
    - 정상:     흰색  — 일반 판매
    - 단골추가: 노란색 — 직원 수동 추가 서비스 포함
    - 할인:     핑크색 — 직원 할인 적용 거래 (기존 VIP 색상 재활용)
    - 환불:     빨간색 — 부분환불/전체취소/교환
    - 마일리지전액: 보라색 — 마일리지만으로 결제 (매장만)
    - 미지급:   파란색 — 서비스 발생했으나 재고 부족
    - 고가팟:   민트색 — 코일(고가) 포함 거래 (적립 없음)
    """
    정상        = "정상"
    단골추가    = "단골추가"
    할인        = "할인"        # 핑크색 — 기존 VIP 재활용
    환불        = "환불"
    마일리지전액 = "마일리지전액"
    미지급      = "미지급"
    고가팟      = "고가팟"      # 민트색


class PaymentNature(str, enum.Enum):
    현금이체            = "현금이체"
    현금이체_카드20이하  = "현금이체_카드20이하"
    카드                = "카드"
    마일리지전액        = "마일리지전액"


class Transaction(Base):
    __tablename__ = "transactions"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    tx_number   = Column(String(20), nullable=False, unique=True,
                         comment="거래번호. 예: 250315-019")
    channel     = Column(Enum(TxChannel), nullable=False)
    status      = Column(Enum(TxStatus), nullable=False, default=TxStatus.완료)
    tx_color    = Column(Enum(TxColor), nullable=False, default=TxColor.정상)

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    staff_id    = Column(Integer, ForeignKey("staff.id"), nullable=False)
    store_id    = Column(Integer, nullable=False, default=1)

    subtotal        = Column(Integer, nullable=False, comment="상품 소계 (할인 전)")
    discount_amount = Column(Integer, nullable=False, default=0,
                             comment=(
                                 "직원 할인 금액 (원). "
                                 "UI에서 양수로 입력 (예: 5000). "
                                 "최대값 = subtotal. "
                                 "total_amount = subtotal - discount_amount - mileage_used."
                             ))
    discount_reason = Column(Text, nullable=True,
                             comment="할인 사유. 필수. 없으면 저장 차단.")
    total_amount    = Column(Integer, nullable=False,
                             comment="최종 결제금액 = subtotal - discount_amount - mileage_used")
    mileage_used    = Column(Integer, nullable=False, default=0)
    mileage_earned  = Column(Integer, nullable=False, default=0)

    payment_nature   = Column(Enum(PaymentNature), nullable=False)
    card_ratio_pct   = Column(Integer, nullable=False, default=0)
    service_eligible = Column(Boolean, nullable=False, default=True)
    earn_eligible    = Column(Boolean, nullable=False, default=False)

    rule_snapshot = Column(JSON, nullable=True,
                           comment="저장 시점 가격/서비스 규칙 스냅샷")

    staff_memo         = Column(Text, nullable=True)
    bonus_service_note = Column(Text, nullable=True,
                                comment="단골 추가 서비스 내용. 있으면 tx_color=단골추가")
    original_tx_id     = Column(Integer, ForeignKey("transactions.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    customer        = relationship("Customer", back_populates="transactions")
    staff           = relationship("Staff", foreign_keys=[staff_id])
    lines           = relationship("TransactionLine", back_populates="transaction")
    payments        = relationship("Payment", back_populates="transaction")
    mileage_ledgers = relationship("MileageLedger", back_populates="transaction")
    service_records = relationship("ServiceRecord", back_populates="transaction")
    unpaid_services = relationship("UnpaidService", back_populates="transaction")
    inventory_moves = relationship("InventoryMove", back_populates="transaction")
    original_tx     = relationship("Transaction", remote_side=[id], foreign_keys=[original_tx_id])

    @property
    def has_discount(self): return self.discount_amount > 0

    def __repr__(self):
        return f"<Transaction {self.tx_number} status={self.status} total={self.total_amount:,}>"
