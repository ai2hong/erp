"""
직원 / 권한 모델 v4 — 멀티스토어 확정 구조

[ 역할 4단계 ]
  사장     : 전 매장 자동 접근 · 모든 권한 · 직원 계정 관리
  총괄     : StaffStoreAccess로 담당 매장 설정 (현재 A·B·C 3개)
             → 추후 매장 추가/제거 시 접근 목록만 수정하면 됨
             승인 권한 전체 보유
  매니저   : StaffStoreAccess로 담당 매장 설정 (1개 이상 가능)
             운영 권한 (일마감 제출, 환불·교환 승인, 입고 처리)
             최종 승인 / 재고 조정 / 직원 관리는 불가
  판매사원 : staff.store_id 고정 → 소속 매장 1곳만 접근
             판매(거래 생성) 전용. 별도 승인 권한 없음.

[ 판매사원 다중 매장 근무 ]
  동일 인물이 여러 매장에서 근무하는 경우 매장별 별도 계정 생성.
  예) 박모씨 → staff_a_park (store_id=1), staff_b_park (store_id=2)
  로그인 시 해당 store_id 기준으로 거래·재고·일마감이 자동 필터링됨.

[ 권한 결정 규칙 ]
  1. 매장 접근 여부 → can_access_store(store_id) 로 API 레이어에서 차단
  2. 기능 권한 여부 → 각 property 로 확인
  두 조건을 모두 통과해야 작업 허용.
"""

from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


# ── 역할 열거형 ──────────────────────────────────────────────
class StaffRole(str, enum.Enum):
    사장     = "사장"
    총괄     = "총괄"
    매니저   = "매니저"
    판매사원 = "판매사원"


# ── 매장 마스터 ──────────────────────────────────────────────
class Store(Base):
    """
    매장 기준 테이블. 현재 3개 운영.
    store_id 는 Staff.store_id / StaffStoreAccess.store_id 의 외래 참조 대상.
    """
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


# ── 직원 본체 ────────────────────────────────────────────────
class Staff(Base):
    __tablename__ = "staff"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    store_id        = Column(Integer, ForeignKey("stores.id"), nullable=False,
                             comment=(
                                 "소속(기본) 매장. "
                                 "판매사원은 이 값으로만 접근 매장 결정. "
                                 "사장·총괄·매니저는 StaffStoreAccess 로 확장."
                             ))
    name            = Column(String(50),  nullable=False)
    login_id        = Column(String(50),  nullable=False, unique=True,
                             comment=(
                                 "전역 고유 ID. "
                                 "판매사원은 매장별 별도 계정 권장. "
                                 "예: staff_hongdae_01, staff_gangnam_01"
                             ))
    hashed_password = Column(String(200), nullable=False)
    role            = Column(Enum(StaffRole), nullable=False, default=StaffRole.판매사원)
    is_active       = Column(Boolean, nullable=False, default=True)
    last_login_at   = Column(DateTime(timezone=True), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    store          = relationship("Store", foreign_keys=[store_id])
    store_accesses = relationship("StaffStoreAccess", back_populates="staff",
                                  cascade="all, delete-orphan")

    # ══════════════════════════════════════════════
    # 매장 접근 제어
    # ══════════════════════════════════════════════

    @property
    def can_access_all(self) -> bool:
        """사장은 StaffStoreAccess 없이 전 매장 접근."""
        return self.role == StaffRole.사장

    def can_access_store(self, store_id: int) -> bool:
        """
        특정 매장 접근 가능 여부.
        API 라우터 의존성 주입(Depends)에서 호출 권장.

        - 사장         : 항상 True
        - 총괄 · 매니저 : StaffStoreAccess 등록 여부
        - 판매사원      : 본인 store_id 일치 여부
        """
        if self.role == StaffRole.사장:
            return True
        if self.role == StaffRole.판매사원:
            return self.store_id == store_id
        # 총괄, 매니저 — StaffStoreAccess 확인
        return any(a.store_id == store_id for a in self.store_accesses)

    def accessible_store_ids(self, all_store_ids: list[int]) -> list[int]:
        """
        접근 가능한 매장 ID 목록 반환.
        QueryFilter / 대시보드 드롭다운 옵션 생성 시 사용.
        """
        if self.role == StaffRole.사장:
            return list(all_store_ids)
        if self.role == StaffRole.판매사원:
            return [self.store_id]
        return [a.store_id for a in self.store_accesses]

    # ══════════════════════════════════════════════
    # 기능별 권한 (role 기반, 매장 접근 체크와 독립)
    # ══════════════════════════════════════════════

    # ── 판매 ────────────────────────────────────
    @property
    def can_create_transaction(self) -> bool:
        """거래(판매) 생성. 전 직원."""
        return self.is_active

    @property
    def can_apply_discount(self) -> bool:
        """직원 할인 입력. 전 직원 가능 (ApprovalLog 자동 생성)."""
        return self.is_active

    # ── 일마감 ───────────────────────────────────
    @property
    def can_submit_dayclose(self) -> bool:
        """일마감 제출. 매니저 이상."""
        return self.role in (StaffRole.사장, StaffRole.총괄, StaffRole.매니저)

    @property
    def can_approve_dayclose(self) -> bool:
        """일마감 최종 승인. 총괄·사장만."""
        return self.role in (StaffRole.사장, StaffRole.총괄)

    # ── 환불·교환 ────────────────────────────────
    @property
    def can_approve_refund_exchange(self) -> bool:
        """
        환불·교환 승인.
        매니저는 현장 처리, 총괄·사장은 원격 최종 승인.
        ApprovalLog.exception_type = 환불승인 / 교환승인
        """
        return self.role in (StaffRole.사장, StaffRole.총괄, StaffRole.매니저)

    @property
    def can_final_approve_exception(self) -> bool:
        """예외 최종 승인 (ApprovalLog 상태 → 승인). 총괄·사장만."""
        return self.role in (StaffRole.사장, StaffRole.총괄)

    # ── 재고 ─────────────────────────────────────
    @property
    def can_process_inbound(self) -> bool:
        """입고 처리. 매니저 이상."""
        return self.role in (StaffRole.사장, StaffRole.총괄, StaffRole.매니저)

    @property
    def can_adjust_inventory(self) -> bool:
        """재고 수동 조정 (InventoryMove.재고조정). 총괄·사장만."""
        return self.role in (StaffRole.사장, StaffRole.총괄)

    @property
    def can_transfer_inventory(self) -> bool:
        """매장간 재고 이동 (InventoryMove.매장간이동출고/입고). 총괄·사장만."""
        return self.role in (StaffRole.사장, StaffRole.총괄)

    # ── 적립금 ───────────────────────────────────
    @property
    def can_adjust_mileage(self) -> bool:
        """적립금 수동 조정. 총괄·사장만."""
        return self.role in (StaffRole.사장, StaffRole.총괄)

    # ── 직원 관리 ────────────────────────────────
    @property
    def can_manage_staff(self) -> bool:
        """
        직원 계정 생성·수정·비활성화.
        사장만 가능. 총괄은 조회만 허용 (API 레이어에서 분리).
        """
        return self.role == StaffRole.사장

    # ── 대시보드 ─────────────────────────────────
    @property
    def can_view_dashboard(self) -> bool:
        """매출 현황 등 집계 대시보드 열람. 매니저 이상."""
        return self.role in (StaffRole.사장, StaffRole.총괄, StaffRole.매니저)

    def __repr__(self):
        return f"<Staff id={self.id} name={self.name} role={self.role} store={self.store_id}>"


# ── 다중 매장 접근 권한 ───────────────────────────────────────
class StaffStoreAccess(Base):
    """
    총괄·매니저가 접근할 수 있는 매장 목록.
    사장    → 불필요 (can_access_all = True).
    판매사원 → 불필요 (staff.store_id 고정).

    [ 운영 시나리오 ]
    총괄 김씨 담당 매장 변경:
      → 기존 StaffStoreAccess 행 삭제 후 새 행 INSERT.
      → Staff 레코드는 수정 불필요.

    매니저 이씨가 신규 매장도 겸임:
      → StaffStoreAccess 행 1개 추가만으로 접근 확장.

    (staff_id, store_id) UNIQUE 로 중복 방지.
    """
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
