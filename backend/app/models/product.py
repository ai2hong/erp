"""
models/product.py — 상품 기준표 모델 v4

v4 변경사항:
  - cost_price (매입 원가) 컬럼 추가  → 마진율 계산 기능
  - supplier (거래처/공급처) 컬럼 추가
  - margin_rate property 추가 (원가 대비 마진율 자동 계산)
  - barcode 컬럼 추가 → 바코드 스캔 입력 기능 대비

분류 15종 및 가격 로직은 v3과 동일.
"""

from typing import Optional

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
    입호흡_기기      = "입호흡 기기"
    폐호흡_기기      = "폐호흡 기기"
    입호흡_기기_단일 = "입호흡 기기(단일가)"
    폐호흡_기기_단일 = "폐호흡 기기(단일가)"
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


# ── 계산 엔진용 분류 집합 ──────────────────────────────────
LIQUID_ALL = {
    ProductCategory.입호흡_이벤트, ProductCategory.입호흡_일반,
    ProductCategory.입호흡_일반_할인제외, ProductCategory.폐호흡_이벤트,
    ProductCategory.폐호흡_일반, ProductCategory.폐호흡_일반_할인제외,
}
LIQUID_EXCL  = {ProductCategory.입호흡_일반_할인제외, ProductCategory.폐호흡_일반_할인제외}
DEVICE_LINKED = {ProductCategory.입호흡_기기, ProductCategory.폐호흡_기기}
DEVICE_FIXED  = {ProductCategory.입호흡_기기_단일, ProductCategory.폐호흡_기기_단일}
DEVICE_ALL    = DEVICE_LINKED | DEVICE_FIXED
HIGH_POD      = {ProductCategory.입호흡_코일_고가, ProductCategory.폐호흡_코일_고가}
EARN_TARGET   = LIQUID_ALL | DEVICE_ALL


class Product(Base):
    __tablename__ = "products"

    id       = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(Enum(ProductCategory), nullable=False, comment="상품 분류 15종")
    name     = Column(String(200), nullable=False)
    barcode  = Column(String(50), nullable=True, unique=True,
                      comment="바코드. 스캐너 입력 시 자동 상품 검색에 사용.")

    # ── 판매가 ──────────────────────────────────────────────
    normal_price = Column(Integer, nullable=False, default=0,
                          comment="정상가 (원)")
    device_discount_price = Column(Integer, nullable=True, default=None,
                                   comment=(
                                       "기기 연동 할인가 (원). "
                                       "입/폐호흡 기기 분류만 입력. "
                                       "단일가 기기는 NULL."
                                   ))

    # ── 원가 / 마진 (사장 전용 필드) ────────────────────────
    cost_price = Column(Integer, nullable=True, default=None,
                        comment=(
                            "매입 원가 (원). 사장·총괄만 열람·수정 가능. "
                            "NULL이면 마진율 계산 불가. "
                            "기기는 매입가, 액상은 박스 단가÷개수로 입력."
                        ))
    supplier   = Column(String(100), nullable=True,
                        comment="거래처·공급사명. 발주 시 참고용.")

    # ── 상태 ────────────────────────────────────────────────
    sale_status = Column(Enum(SaleStatus), nullable=False, default=SaleStatus.판매중)
    memo        = Column(Text, nullable=True, comment="내부 메모")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    transaction_lines = relationship("TransactionLine", back_populates="product")
    inventory         = relationship("Inventory", back_populates="product", uselist=False)
    inventory_moves   = relationship("InventoryMove", back_populates="product")

    # ── 분류 판별 프로퍼티 ───────────────────────────────────
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
    def safe_device_price(self) -> int:
        """연동 할인가 검증 — 없거나 정상가 이상이면 정상가 반환."""
        d = self.device_discount_price
        if d and 0 < d < self.normal_price:
            return d
        return self.normal_price

    # ── 마진율 프로퍼티 (원가 있을 때만) ────────────────────
    @property
    def margin_amount(self) -> Optional[int]:
        """
        마진 금액 (원) = 정상가 - 원가.
        원가 미입력 시 None.
        """
        if self.cost_price is None or self.cost_price <= 0:
            return None
        return self.normal_price - self.cost_price

    @property
    def margin_rate(self) -> Optional[float]:
        """
        마진율 (%) = (정상가 - 원가) / 정상가 × 100.
        원가 또는 정상가 미입력 시 None.

        예: 정상가 20,000 / 원가 12,000 → 마진율 40.0%
        """
        if self.cost_price is None or self.cost_price <= 0:
            return None
        if self.normal_price <= 0:
            return None
        return round((self.normal_price - self.cost_price) / self.normal_price * 100, 1)

    @property
    def device_discount_margin_rate(self) -> Optional[float]:
        """
        기기 연동할인가 기준 마진율.
        기기 분류이고 원가 + 할인가 모두 있을 때만 계산.
        """
        if not self.is_device_linked:
            return None
        if self.cost_price is None or self.cost_price <= 0:
            return None
        dp = self.device_discount_price
        if not dp or dp <= 0:
            return None
        return round((dp - self.cost_price) / dp * 100, 1)

    def __repr__(self):
        margin = f" margin={self.margin_rate}%" if self.margin_rate else ""
        return f"<Product id={self.id} name={self.name} category={self.category}{margin}>"
