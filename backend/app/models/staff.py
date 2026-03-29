"""
직원 / 권한 모델 — 5단계 권한 구조

[ 역할 5단계 ]
  관리자 : 시스템 전체 최상위. 전 매장 + 사장 계정 관리 포함.
  사장   : 전 매장 자동 접근 · 운영 전권 · 직원 계정 관리
  총괄   : StaffStoreAccess로 담당 매장 설정. 승인 권한 전체 보유.
  시니어 : StaffStoreAccess로 담당 매장 설정 (1개 이상 가능)
           운영 권한 (일마감 제출, 환불·교환 처리, 입고 처리)
  매니저 : staff.store_id 고정 → 소속 매장 1곳만 접근
           판매(거래 생성) 전용.
"""
from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class StaffRole(str, enum.Enum):
    관리자 = "관리자"  # 시스템 최상위 (서버 관리자)
    사장   = "사장"    # 매장 오너
    총괄   = "총괄"    # 전체 운영 담당
    시니어 = "시니어"  # 선임 (구 매니저)
    매니저 = "매니저"  # 일반 판매직 (구 판매사원)


class Store(Base):
    __tablename__ = "stores"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    name      = Column(String(100), nullable=False, comment="매장명. 예: 증산점, 양산점, 범어점")
    address   = Column(String(300), nullable=True)
    phone     = Column(String(20),  nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Store id={self.id} name={self.name}>"


class Staff(Base):
    __tablename__ = "staff"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    store_id        = Column(Integer, ForeignKey("stores.id"), nullable=False,
                             comment="소속(기본) 매장. 매니저는 이 값으로만 접근 매장 결정.")
    name            = Column(String(50),  nullable=False)
    login_id        = Column(String(50),  nullable=False, unique=True)
    hashed_password = Column(String(200), nullable=False)
    role            = Column(Enum(StaffRole), nullable=False, default=StaffRole.매니저)
    is_active       = Column(Boolean, nullable=False, default=True)
    last_login_at   = Column(DateTime(timezone=True), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    store          = relationship("Store", foreign_keys=[store_id])
    store_accesses = relationship("StaffStoreAccess", back_populates="staff",
                                  cascade="all, delete-orphan")

    # ── 매장 접근 제어 ──────────────────────────────────────

    @property
    def can_access_all(self) -> bool:
        """관리자·사장은 전 매장 접근."""
        return self.role in (StaffRole.관리자, StaffRole.사장)

    def can_access_store(self, store_id: int) -> bool:
        if self.role in (StaffRole.관리자, StaffRole.사장):
            return True
        if self.role == StaffRole.매니저:
            return self.store_id == store_id
        # 총괄·시니어 — StaffStoreAccess 확인
        return any(a.store_id == store_id for a in self.store_accesses)

    def accessible_store_ids(self, all_store_ids: list) -> list:
        if self.role in (StaffRole.관리자, StaffRole.사장):
            return list(all_store_ids)
        if self.role == StaffRole.매니저:
            return [self.store_id]
        return [a.store_id for a in self.store_accesses]

    # ── 기능별 권한 ─────────────────────────────────────────

    @property
    def can_create_transaction(self) -> bool:
        """거래 생성. 전 직원."""
        return self.is_active

    @property
    def can_apply_discount(self) -> bool:
        """직원 할인 입력. 전 직원 (ApprovalLog 자동 생성)."""
        return self.is_active

    @property
    def can_submit_dayclose(self) -> bool:
        """일마감 제출. 시니어 이상."""
        return self.role in (StaffRole.관리자, StaffRole.사장, StaffRole.총괄, StaffRole.시니어)

    @property
    def can_approve_dayclose(self) -> bool:
        """일마감 최종 승인. 총괄 이상."""
        return self.role in (StaffRole.관리자, StaffRole.사장, StaffRole.총괄)

    @property
    def can_approve_refund_exchange(self) -> bool:
        """환불·교환 승인. 시니어 이상."""
        return self.role in (StaffRole.관리자, StaffRole.사장, StaffRole.총괄, StaffRole.시니어)

    @property
    def can_final_approve_exception(self) -> bool:
        """예외 최종 승인. 총괄 이상."""
        return self.role in (StaffRole.관리자, StaffRole.사장, StaffRole.총괄)

    @property
    def can_process_inbound(self) -> bool:
        """입고 처리. 시니어 이상."""
        return self.role in (StaffRole.관리자, StaffRole.사장, StaffRole.총괄, StaffRole.시니어)

    @property
    def can_adjust_inventory(self) -> bool:
        """재고 수동 조정. 총괄 이상."""
        return self.role in (StaffRole.관리자, StaffRole.사장, StaffRole.총괄)

    @property
    def can_transfer_inventory(self) -> bool:
        """택배·배달 이동 처리. 총괄 이상."""
        return self.role in (StaffRole.관리자, StaffRole.사장, StaffRole.총괄)

    @property
    def can_adjust_mileage(self) -> bool:
        """적립금 수동 조정. 총괄 이상."""
        return self.role in (StaffRole.관리자, StaffRole.사장, StaffRole.총괄)

    @property
    def can_manage_staff(self) -> bool:
        """직원 계정 생성·수정. 사장 이상."""
        return self.role in (StaffRole.관리자, StaffRole.사장)

    @property
    def can_view_dashboard(self) -> bool:
        """대시보드 열람. 시니어 이상."""
        return self.role in (StaffRole.관리자, StaffRole.사장, StaffRole.총괄, StaffRole.시니어)

    def __repr__(self):
        return f"<Staff id={self.id} name={self.name} role={self.role} store={self.store_id}>"


class StaffStoreAccess(Base):
    """총괄·시니어가 접근할 수 있는 매장 목록."""
    __tablename__ = "staff_store_accesses"
    __table_args__ = (
        UniqueConstraint("staff_id", "store_id", name="uq_staff_store"),
    )

    id         = Column(Integer, primary_key=True, autoincrement=True)
    staff_id   = Column(Integer, ForeignKey("staff.id"),  nullable=False)
    store_id   = Column(Integer, ForeignKey("stores.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    staff = relationship("Staff", back_populates="store_accesses")
    store = relationship("Store")

    def __repr__(self):
        return f"<StaffStoreAccess staff={self.staff_id} → store={self.store_id}>"
