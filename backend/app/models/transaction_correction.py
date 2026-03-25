"""
models/transaction_correction.py — 거래 정정 모델

거래 정정 흐름:
  1. 직원이 완료된 거래에서 오류 발견 → 정정 요청 생성
  2. 정정 전 스냅샷 저장 (before_snapshot)
  3. 매니저/총괄이 승인 → 원거래 수정 + 정정완료 표시
  4. 정정 후 스냅샷 저장 (after_snapshot)
  5. 차이 금액 → 재고·적립금·일마감에 반영

정정 가능 항목:
  - 품목 수량 변경 (입력 실수)
  - 채널 변경 (매장→배달 등 오입력)
  - 결제 수단 변경
  - 할인 금액 수정

정정 불가 항목:
  - 이미 환불·교환된 거래
  - 전일 이전 거래 (당일만 가능, 정책에 따라 조정)
  - 이미 정정완료된 거래의 재정정
"""

from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class CorrectionStatus(str, enum.Enum):
    대기   = "대기"    # 정정 요청 접수, 승인 전
    승인   = "승인"    # 원거래 수정 완료
    반려   = "반려"    # 반려 (원거래 변경 없음)


class CorrectionType(str, enum.Enum):
    수량변경   = "수량변경"    # 품목 수량 오입력
    채널변경   = "채널변경"    # 매장/배달/택배 오입력
    결제변경   = "결제변경"    # 결제수단 오입력
    할인변경   = "할인변경"    # 할인 금액 수정
    기타       = "기타"


class TransactionCorrection(Base):
    """
    거래 정정 요청·이력 테이블.

    before_snapshot / after_snapshot:
      JSON 형식으로 정정 전·후 거래 상태 전체를 스냅샷 저장.
      분쟁·감사 추적 시 사용.

    amount_diff:
      정정으로 인한 금액 변화 (원).
      양수 = 추가 결제 필요, 음수 = 환불 필요.
    """
    __tablename__ = "transaction_corrections"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 원거래 연결 ─────────────────────────────────────────
    transaction_id   = Column(Integer, ForeignKey("transactions.id"), nullable=False,
                              comment="정정 대상 원거래")
    correction_type  = Column(Enum(CorrectionType), nullable=False)
    status           = Column(Enum(CorrectionStatus), nullable=False,
                              default=CorrectionStatus.대기)

    # ── 정정 내용 ────────────────────────────────────────────
    correction_reason = Column(Text, nullable=False,
                                comment="정정 사유. 필수. 예: '수량 2병→3병 오입력'")
    before_snapshot   = Column(JSON, nullable=True,
                                comment=(
                                    "정정 전 거래 상태 스냅샷. "
                                    "{ lines: [...], total_amount, channel, payments, ... }"
                                ))
    after_snapshot    = Column(JSON, nullable=True,
                                comment="정정 후 거래 상태 스냅샷. 승인 시 채워짐.")

    amount_diff = Column(Integer, nullable=False, default=0,
                         comment=(
                             "금액 변화 (원). "
                             "양수 = 고객 추가 결제, 음수 = 환불. "
                             "0 = 금액 변동 없음 (채널 변경 등)."
                         ))
    mileage_diff = Column(Integer, nullable=False, default=0,
                          comment=(
                              "적립금 변화 (원). "
                              "정정으로 인해 적립금을 추가 적립하거나 회수할 때 사용."
                          ))

    # ── 요청·승인 ────────────────────────────────────────────
    requested_by  = Column(Integer, ForeignKey("staff.id"), nullable=False,
                            comment="정정 요청 직원")
    approved_by   = Column(Integer, ForeignKey("staff.id"), nullable=True,
                            comment="정정 승인 매니저·총괄")
    approval_note = Column(Text, nullable=True, comment="승인자 메모")
    rejected_reason = Column(Text, nullable=True, comment="반려 사유")

    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True,
                          comment="승인 또는 반려 처리 시각")

    transaction = relationship("Transaction", foreign_keys=[transaction_id])
    requester   = relationship("Staff", foreign_keys=[requested_by])
    approver    = relationship("Staff", foreign_keys=[approved_by])

    def __repr__(self):
        return (f"<TxCorrection tx={self.transaction_id} "
                f"type={self.correction_type} status={self.status}>")
