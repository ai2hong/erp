"""
매장간 재고 이동 모델 — store_transfers 테이블

흐름:
  1. 신청 (서면점 직원)     → status = 신청
  2. 발송 (증산점 직원)     → status = 발송중  + 증산점 재고 -qty (택배배달출고)
  3. 수령 (서면점 직원)     → status = 수령완료 + 서면점 재고 +qty (택배배달입고)
  4. 월말 정산 (증산점 총괄) → fee_settled = True

재고 반영:
  - 발송 처리 시: from_store 재고 차감 (InventoryMove.택배배달출고)
  - 수령 처리 시: to_store   재고 증가 (InventoryMove.택배배달입고)

택배비 정산:
  - 1건당 delivery_fee (기본 2,500원) + 입고단가 × 수량
  - 월말에 GET /transfers/fee-summary?month=YYYY-MM 으로 집계
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Enum,
    DateTime, Text, ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class TransferMethod(str, enum.Enum):
    택배 = "택배"   # 건당 2,500원 — 증산점 총괄 처리
    배달 = "배달"   # 직접 배달 — 택배비 없음
    # 나중에 추가 가능: 퀵서비스 = "퀵서비스"


class TransferStatus(str, enum.Enum):
    신청   = "신청"    # 요청 접수
    발송중 = "발송중"  # 출발 매장에서 발송 처리 + 재고 차감
    수령완료 = "수령완료"  # 도착 매장에서 수령 확인 + 재고 증가
    취소   = "취소"    # 발송 전 취소만 가능


class StoreTransfer(Base):
    __tablename__ = "store_transfers"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    transfer_number = Column(
        String(20), nullable=False, unique=True,
        comment="이동번호. 예: TF-250327-001"
    )

    # ── 매장 정보 ──────────────────────────────────
    from_store_id = Column(Integer, ForeignKey("stores.id"), nullable=False,
                           comment="출발 매장 (보내는 쪽)")
    to_store_id   = Column(Integer, ForeignKey("stores.id"), nullable=False,
                           comment="도착 매장 (받는 쪽)")

    # ── 상품 정보 ──────────────────────────────────
    product_id    = Column(Integer, ForeignKey("products.id"), nullable=False)
    qty           = Column(Integer, nullable=False, comment="이동 수량")
    unit_cost     = Column(Integer, nullable=False, default=0,
                           comment="입고단가 (원). 월말 정산 기준.")

    # ── 이동 방법 + 사유 ───────────────────────────
    transfer_method = Column(Enum(TransferMethod), nullable=False,
                             comment="택배 | 배달")
    reason          = Column(Text, nullable=False,
                             comment="이동 사유. 필수. 예: 서면점 고객 주문, 재고 조정")

    # ── 상태 ───────────────────────────────────────
    status = Column(Enum(TransferStatus), nullable=False,
                    default=TransferStatus.신청)

    # ── 택배비 정산 ────────────────────────────────
    delivery_fee    = Column(Integer, nullable=False, default=2500,
                             comment="건당 택배비 (원). 기본 2,500원")
    fee_settled     = Column(Boolean, nullable=False, default=False,
                             comment="택배비 정산 완료 여부")
    fee_settled_month = Column(String(7), nullable=True,
                               comment="정산 완료 월. 예: 2025-03")

    # ── 담당자 ─────────────────────────────────────
    requested_by = Column(Integer, ForeignKey("staff.id"), nullable=False,
                          comment="신청자 (도착 매장 직원)")
    shipped_by   = Column(Integer, ForeignKey("staff.id"), nullable=True,
                          comment="발송 처리자 (출발 매장 직원)")
    received_by  = Column(Integer, ForeignKey("staff.id"), nullable=True,
                          comment="수령 처리자 (도착 매장 직원)")
    cancelled_by = Column(Integer, ForeignKey("staff.id"), nullable=True)

    # ── 재고 이동 연결 ─────────────────────────────
    ship_move_id    = Column(Integer, ForeignKey("inventory_moves.id"), nullable=True,
                             comment="발송 시 생성된 InventoryMove (출고)")
    receive_move_id = Column(Integer, ForeignKey("inventory_moves.id"), nullable=True,
                             comment="수령 시 생성된 InventoryMove (입고)")

    # ── 메모 + 타임스탬프 ─────────────────────────
    memo         = Column(Text, nullable=True)
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    shipped_at   = Column(DateTime(timezone=True), nullable=True)
    received_at  = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(Text, nullable=True)

    # ── 관계 ───────────────────────────────────────
    from_store   = relationship("Store", foreign_keys=[from_store_id])
    to_store     = relationship("Store", foreign_keys=[to_store_id])
    product      = relationship("Product")
    requester    = relationship("Staff", foreign_keys=[requested_by])
    shipper      = relationship("Staff", foreign_keys=[shipped_by])
    receiver     = relationship("Staff", foreign_keys=[received_by])
    canceller    = relationship("Staff", foreign_keys=[cancelled_by])
    ship_move    = relationship("InventoryMove", foreign_keys=[ship_move_id])
    receive_move = relationship("InventoryMove", foreign_keys=[receive_move_id])

    @property
    def total_cost(self):
        """정산 총액 = (입고단가 × 수량) + 택배비"""
        if self.transfer_method == TransferMethod.택배:
            return (self.unit_cost * self.qty) + self.delivery_fee
        return self.unit_cost * self.qty

    def __repr__(self):
        return (f"<StoreTransfer {self.transfer_number} "
                f"{self.from_store_id}→{self.to_store_id} "
                f"qty={self.qty} status={self.status}>")
