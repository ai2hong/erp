"""재고 이동 이력 모델 — DB 스키마에 맞춰 수정 (inventory_moves 테이블)"""
from sqlalchemy import Column, Integer, Enum, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class MoveType(str, enum.Enum):
    입고           = "입고"
    판매출고       = "판매출고"
    서비스출고     = "서비스출고"
    단골추가출고   = "단골추가출고"
    보상출고       = "보상출고"
    교환회수       = "교환회수"
    교환출고       = "교환출고"
    예약할당       = "예약할당"
    예약수령       = "예약수령"
    재고조정       = "재고조정"
    택배배달출고   = "택배배달출고"
    택배배달입고   = "택배배달입고"
    폐기           = "폐기"
    환불반입       = "환불반입"


class InventoryMove(Base):
    __tablename__ = "inventory_moves"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    store_id   = Column(Integer, nullable=False, default=1)

    transaction_id     = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    move_type          = Column(Enum(MoveType), nullable=False)
    quantity           = Column(Integer, nullable=False)
    quantity_before    = Column(Integer, nullable=False)
    quantity_after     = Column(Integer, nullable=False)

    counterpart_store_id = Column(Integer, nullable=True)
    staff_id             = Column(Integer, ForeignKey("staff.id"), nullable=True)
    note                 = Column(Text, nullable=True)
    created_at           = Column(DateTime(timezone=True), server_default=func.now())

    product     = relationship("Product", back_populates="inventory_moves")
    transaction = relationship("Transaction", back_populates="inventory_moves")
    staff       = relationship("Staff", foreign_keys=[staff_id])

    def __repr__(self):
        return (f"<InventoryMove id={self.id} type={self.move_type} "
                f"qty={self.quantity:+d} {self.quantity_before}→{self.quantity_after}>")
