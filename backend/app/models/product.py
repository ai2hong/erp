"""
상품 기준표 모델 v4

v4 변경:
- inventory 관계 uselist=False → uselist=True (inventories) 로 변경
  → inventory.py 멀티스토어 수정에 맞춰 매장별 재고 리스트 반환

v3 변경:
- 입호흡 기기(단일가) / 폐호흡 기기(단일가) 추가
  → 액상 자격 무관, device_discount_price 없음, normal_price만 사용
- 기기 연동 할인 대수 공식 변경
  → floor(자격병수 / 3) × 2 대
  → 총괄 승인 규칙 폐지
"""

from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, Text, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ProductCategory(str, enum.Enum):
    # 액상 6종
    입호흡_이벤트        = "입호흡 이벤트"
    입호흡_일반          = "입호흡 일반"
    입호흡_일반_할인제외  = "입호흡 일반(할인제외)"
    폐호흡_이벤트        = "폐호흡 이벤트"
    폐호흡_일반          = "폐호흡 일반"
    폐호흡_일반_할인제외  = "폐호흡 일반(할인제외)"
    # 기기 4종
    입호흡_기기      = "입호흡 기기"        # 슬래시 가격 — 액상 3병+ 시 할인가
    폐호흡_기기      = "폐호흡 기기"        # 슬래시 가격 — 액상 3병+ 시 할인가
    입호흡_기기_단일 = "입호흡 기기(단일가)" # 단일 가격 — 액상 자격 무관
    폐호흡_기기_단일 = "폐호흡 기기(단일가)" # 단일 가격 — 액상 자격 무관
    # 코일 4종
    입호흡_코일      = "입호흡 코일"
    입호흡_코일_고가  = "입호흡 코일(고가)"
    폐호흡_코일      = "폐호흡 코일"
    폐호흡_코일_고가  = "폐호흡 코일(고가)"
    # 기타
    악세사리 = "악세사리"


class SaleStatus(str, enum.Enum):
    판매중 = "판매중"
    품절   = "품절"
    단종   = "단종"


# ── 계산 엔진용 분류 집합 ──────────────────────────────
LIQUID_ALL  = {
    ProductCategory.입호흡_이벤트,
    ProductCategory.입호흡_일반,
    ProductCategory.입호흡_일반_할인제외,
    ProductCategory.폐호흡_이벤트,
    ProductCategory.폐호흡_일반,
    ProductCategory.폐호흡_일반_할인제외,
}
LIQUID_EXCL = {
    ProductCategory.입호흡_일반_할인제외,
    ProductCategory.폐호흡_일반_할인제외,
}
# 연동 할인 기기 (슬래시 가격)
DEVICE_LINKED = {
    ProductCategory.입호흡_기기,
    ProductCategory.폐호흡_기기,
}
# 단일가 기기 (액상 자격 무관)
DEVICE_FIXED = {
    ProductCategory.입호흡_기기_단일,
    ProductCategory.폐호흡_기기_단일,
}
DEVICE_ALL  = DEVICE_LINKED | DEVICE_FIXED
HIGH_POD    = {
    ProductCategory.입호흡_코일_고가,
    ProductCategory.폐호흡_코일_고가,
}
EARN_TARGET = LIQUID_ALL | DEVICE_ALL


class Product(Base):
    __tablename__ = "products"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    category     = Column(
        Enum(ProductCategory), nullable=False,
        comment="상품 분류 15종"
    )
    name         = Column(String(200), nullable=False)
    normal_price = Column(Integer, nullable=False, default=0, comment="정상가 (원)")
    device_discount_price = Column(
        Integer, nullable=True, default=None,
        comment=(
            "기기 연동 할인가 (원). "
            "입/폐호흡 기기 분류만 입력. "
            "단일가 기기는 NULL. "
            "슬래시 앞 숫자: 38,000/42,000 → 38,000"
        )
    )
    sale_status  = Column(Enum(SaleStatus), nullable=False, default=SaleStatus.판매중)
    memo         = Column(Text, nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())

    transaction_lines = relationship("TransactionLine", back_populates="product")
    inventories       = relationship("Inventory", back_populates="product")  # 매장별 복수
    inventory_moves   = relationship("InventoryMove", back_populates="product")

    @property
    def is_liquid(self):        return self.category in LIQUID_ALL
    @property
    def is_excluded(self):      return self.category in LIQUID_EXCL
    @property
    def is_device(self):        return self.category in DEVICE_ALL
    @property
    def is_device_linked(self): return self.category in DEVICE_LINKED
    @property
    def is_device_fixed(self):  return self.category in DEVICE_FIXED
    @property
    def is_high_pod(self):      return self.category in HIGH_POD
    @property
    def is_earn_eligible(self): return self.category in EARN_TARGET

    @property
    def safe_device_price(self):
        """연동 할인가 검증 — 없거나 정상가 이상이면 정상가"""
        d = self.device_discount_price
        if d and 0 < d < self.normal_price:
            return d
        return self.normal_price

    def __repr__(self):
        return f"<Product id={self.id} name={self.name} category={self.category}>"
