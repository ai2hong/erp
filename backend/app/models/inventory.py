"""
models/inventory.py — 매장별 상품 재고 현황

매장 × 상품 조합으로 현재 재고 수량 추적.
재고 변동은 InventoryMove에 기록, 이 테이블은 현재 수량만 유지.
"""

from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.database import Base


class Inventory(Base):
    __tablename__ = "inventories"
    __table_args__ = (
        UniqueConstraint("store_id", "product_id", name="uq_inventory_store_product"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    quantity = Column(Integer, nullable=False, default=0,
                      comment="현재 재고 수량. 음수 허용 (긴급 판매 시).")
    safety_stock = Column(Integer, nullable=True, default=None,
                          comment="안전 재고 수량. 이 이하일 때 알림.")

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── 관계 ────────────────────────────────────────────────
    store = relationship("Store")
    product = relationship("Product", back_populates="inventory")

    @property
    def is_low_stock(self) -> bool:
        """안전 재고 이하 여부."""
        if self.safety_stock is None:
            return False
        return self.quantity <= self.safety_stock

    def __repr__(self):
        return f"<Inventory store={self.store_id} product={self.product_id} qty={self.quantity}>"
