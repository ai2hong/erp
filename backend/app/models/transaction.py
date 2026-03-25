"""
models/transaction.py — 거래 헤더 모델 v3

v3 변경사항:
  - store_id → ForeignKey("stores.id") 로 변경 (FK 누락 수정)
  - staff_memo 컬럼 주석 강화 (UI에서 편집 가능함을 명시)
  - adult_verified 컬럼 추가 (성인 인증 확인 기록)
  - corrected_from_tx_id 컬럼 추가 (정정 원거래 참조)

나머지 구조는 v2와 동일.
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
    정상         = "정상"
    단골추가     = "단골추가"
    할인         = "할인"
    환불         = "환불"
    마일리지전액  = "마일리지전액"
    미지급       = "미지급"
    고가팟       = "고가팟"


class PaymentNature(str, enum.Enum):
    현금이체           = "현금이체"
    현금이체_카드20이하 = "현금이체_카드20이하"
    카드               = "카드"
    마일리지전액       = "마일리지전액"


class Transaction(Base):
    __tablename__ = "transactions"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    tx_number = Column(String(20), nullable=False, unique=True,
                       comment="거래번호. 예: 250315-019")
    channel   = Column(Enum(TxChannel), nullable=False)
    status    = Column(Enum(TxStatus), nullable=False, default=TxStatus.완료)
    tx_color  = Column(Enum(TxColor), nullable=False, default=TxColor.정상)

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    staff_id    = Column(Integer, ForeignKey("staff.id"), nullable=False)
    store_id    = Column(Integer, ForeignKey("stores.id"), nullable=False,
                         comment="거래 발생 매장. FK 연결 필수.")   # ← v2에서 FK 누락 수정

    # ── 금액 ────────────────────────────────────────────────
    subtotal = Column(Integer, nullable=False, comment="상품 소계 (할인 전, 원)")
    discount_amount = Column(Integer, nullable=False, default=0,
                             comment=(
                                 "직원 할인 금액 (원). 양수 입력. "
                                 "최대값 = subtotal. "
                                 "사유 없으면 저장 차단."
                             ))
    discount_reason = Column(Text, nullable=True,
                             comment="할인 사유. discount_amount > 0 이면 필수.")
    total_amount    = Column(Integer, nullable=False,
                             comment="최종 결제금액 = subtotal - discount_amount - mileage_used")
    mileage_used    = Column(Integer, nullable=False, default=0, comment="사용 적립금 (원)")
    mileage_earned  = Column(Integer, nullable=False, default=0, comment="적립 금액 (원)")

    payment_nature   = Column(Enum(PaymentNature), nullable=False)
    card_ratio_pct   = Column(Integer, nullable=False, default=0,
                              comment="카드 비중 (%). 0~100")
    service_eligible = Column(Boolean, nullable=False, default=True,
                              comment="서비스 자격 여부")
    earn_eligible    = Column(Boolean, nullable=False, default=False,
                              comment="적립 가능 여부")

    # ── 직원 메모 / 특이사항 ─────────────────────────────────
    staff_memo = Column(Text, nullable=True,
                        comment=(
                            "직원 메모 / 특이사항. POS 저장 화면에서 입력 가능. "
                            "예: '다음 방문 시 OOO 문의', '기기 색상 확인 요망' 등. "
                            "거래 상세 조회 화면에서도 수정 가능 (당일 한정)."
                        ))

    # ── 성인 인증 ────────────────────────────────────────────
    adult_verified = Column(Boolean, nullable=False, default=False,
                            comment=(
                                "성인 인증 확인 여부. "
                                "판매 완료 전 직원이 체크. "
                                "법적 의무 기록."
                            ))

    # ── 정정 연결 ─────────────────────────────────────────────
    original_tx_id = Column(Integer, ForeignKey("transactions.id"), nullable=True,
                            comment="정정·환불의 원거래 ID")

    # ── 스냅샷 ───────────────────────────────────────────────
    rule_snapshot = Column(JSON, nullable=True,
                           comment="저장 시점 가격/서비스 규칙 스냅샷 (감사 추적용)")
    bonus_service_note = Column(Text, nullable=True,
                                comment="단골 추가 서비스 내용. 있으면 tx_color=단골추가")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ── 관계 ────────────────────────────────────────────────
    customer        = relationship("Customer", back_populates="transactions")
    staff           = relationship("Staff", foreign_keys=[staff_id])
    store           = relationship("Store")
    lines           = relationship("TransactionLine", back_populates="transaction")
    payments        = relationship("Payment", back_populates="transaction")
    mileage_ledgers = relationship("MileageLedger", back_populates="transaction")
    service_records = relationship("ServiceRecord", back_populates="transaction")
    unpaid_services = relationship("UnpaidService", back_populates="transaction",
                                   foreign_keys="[UnpaidService.transaction_id]")
    inventory_moves = relationship("InventoryMove", back_populates="transaction")
    original_tx     = relationship("Transaction", remote_side=[id],
                                   foreign_keys=[original_tx_id])

    # ── 프로퍼티 ─────────────────────────────────────────────
    @property
    def has_discount(self) -> bool:
        return self.discount_amount > 0

    @property
    def has_memo(self) -> bool:
        return bool(self.staff_memo and self.staff_memo.strip())

    def __repr__(self):
        return f"<Transaction {self.tx_number} status={self.status} total={self.total_amount:,}>"
