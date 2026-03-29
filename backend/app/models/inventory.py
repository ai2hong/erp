"""재고 모델 — DB 스키마에 맞춰 수정 (inventories 테이블)"""
from sqlalchemy import Column, Integer, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.database import Base


class Inventory(Base):
    __tablename__ = "inventories"
    __table_args__ = (
        UniqueConstraint("product_id", "store_id", name="uq_inventory_product_store"),
    )

    id           = Column(Integer, primary_key=True, autoincrement=True)
    product_id   = Column(Integer, ForeignKey("products.id"), nullable=False)
    store_id     = Column(Integer, nullable=False, default=1)

    quantity     = Column(Integer, nullable=False, default=0, comment="실재고")
    safety_stock = Column(Integer, nullable=False, default=0, comment="안전재고")

    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())

    product = relationship("Product", back_populates="inventories")

    @property
    def qty_actual(self):
        return self.quantity

    @property
    def qty_available(self):
        return self.quantity

    @property
    def qty_undelivered(self):
        return 0

    @property
    def qty_reserved(self):
        return 0

    @property
    def is_shortage(self):
        ss = self.safety_stock or 0
        return self.quantity <= ss and ss > 0

    @property
    def is_out_of_stock(self):
        return self.quantity == 0

    def __repr__(self):
        return f"<Inventory store={self.store_id} product={self.product_id} qty={self.quantity}>"
