"""
models/inventory_move.py — 재고 변동 이력

입고, 판매차감, 환불복원, 매장간이동, 재고조정 등
모든 재고 변동을 기록하는 원장.
"""

from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class MoveType(str, enum.Enum):
    입고 = "입고"
    판매차감 = "판매차감"
    환불복원 = "환불복원"
    매장간이동출고 = "매장간이동출고"
    매장간이동입고 = "매장간이동입고"
    재고조정 = "재고조정"
    서비스차감 = "서비스차감"


class InventoryMove(Base):
    __tablename__ = "inventory_moves"

    id = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False,
                      comment="재고 변동 발생 매장")
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True,
                            comment="연관 거래. 입고·조정 시 NULL.")

    move_type = Column(Enum(MoveType), nullable=False)
    quantity = Column(Integer, nullable=False,
                      comment="변동 수량. 입고=양수, 차감=음수.")
    quantity_before = Column(Integer, nullable=False,
                             comment="변동 전 재고 수량")
    quantity_after = Column(Integer, nullable=False,
                            comment="변동 후 재고 수량")

    note = Column(Text, nullable=True, comment="변동 사유·메모")
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=False,
                      comment="처리 직원")

    # 매장간 이동 시 상대 매장
    counterpart_store_id = Column(Integer, ForeignKey("stores.id"), nullable=True,
                                  comment="매장간 이동 시 상대 매장 ID")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── 관계 ────────────────────────────────────────────────
    store = relationship("Store", foreign_keys=[store_id])
    product = relationship("Product", back_populates="inventory_moves")
    transaction = relationship("Transaction", back_populates="inventory_moves")
    staff = relationship("Staff", foreign_keys=[staff_id])
    counterpart_store = relationship("Store", foreign_keys=[counterpart_store_id])

    def __repr__(self):
        return (f"<InventoryMove store={self.store_id} product={self.product_id} "
                f"type={self.move_type} qty={self.quantity}>")
