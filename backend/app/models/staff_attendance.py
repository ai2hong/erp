"""
models/staff_attendance.py — 직원 출퇴근 기록 모델

동작 방식:
  - 로그인 시 자동 출근 기록 (또는 직원이 수동 출근 버튼 클릭)
  - 로그아웃 시 자동 퇴근 기록 (또는 직원이 수동 퇴근 버튼 클릭)
  - 비정상 종료(브라우저 닫기 등)는 다음 날 09:00에 자동 퇴근 처리 (cron)

분리 이유:
  LoginHistory: 보안 목적 (이상 접근 감지)
  StaffAttendance: 근태 목적 (근무 시간 추적)
  → 두 테이블을 분리해 목적을 명확히 함

권한:
  - 본인: 본인 기록만 조회
  - 매니저: 담당 매장 직원 조회
  - 총괄·사장: 전체 조회 + 수동 정정
"""

from sqlalchemy import (
    Column, Integer, String, Enum, DateTime,
    Date, Text, ForeignKey, Boolean, func
)
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class AttendanceType(str, enum.Enum):
    출근 = "출근"
    퇴근 = "퇴근"


class AttendanceSource(str, enum.Enum):
    자동_로그인  = "자동_로그인"   # 로그인 시 자동 기록
    자동_로그아웃 = "자동_로그아웃" # 로그아웃 시 자동 기록
    자동_만료    = "자동_만료"     # 세션 만료 시 자동 퇴근 처리
    수동         = "수동"          # 직원/매니저가 직접 입력


class StaffAttendance(Base):
    """
    직원 출퇴근 기록.

    하루에 출근 1건 + 퇴근 1건이 기본.
    중간에 외출·재입실이 있는 경우 여러 건 생성 가능.

    work_minutes:
      퇴근 기록 시 직전 출근 기록과의 차이로 자동 계산.
      출근 기록에는 NULL.
    """
    __tablename__ = "staff_attendances"

    id       = Column(Integer, primary_key=True, autoincrement=True)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False,
                      comment="기록 시점 소속 매장")
    work_date = Column(Date, nullable=False, comment="근무 날짜 (출근 기준)")

    att_type  = Column(Enum(AttendanceType), nullable=False, comment="출근 or 퇴근")
    att_time  = Column(DateTime(timezone=True), nullable=False, comment="출근·퇴근 시각")
    source    = Column(Enum(AttendanceSource), nullable=False,
                       default=AttendanceSource.자동_로그인,
                       comment="기록 출처 — 자동(로그인/로그아웃) or 수동")

    # 퇴근 기록에만 채워짐
    work_minutes = Column(Integer, nullable=True,
                          comment=(
                              "근무 시간 (분). 퇴근 시 직전 출근과의 차이로 계산. "
                              "출근 기록은 NULL."
                          ))
    paired_id    = Column(Integer, ForeignKey("staff_attendances.id"), nullable=True,
                          comment="출근↔퇴근 쌍 ID. 퇴근 기록이 대응 출근 기록을 참조.")

    # 수동 정정 필드
    is_corrected  = Column(Boolean, nullable=False, default=False,
                           comment="수동 정정 여부")
    corrected_by  = Column(Integer, ForeignKey("staff.id"), nullable=True,
                           comment="정정한 매니저·총괄 ID")
    correction_note = Column(Text, nullable=True, comment="정정 사유")
    original_time   = Column(DateTime(timezone=True), nullable=True,
                             comment="정정 전 원본 시각. 감사 추적용.")

    ip_address = Column(String(45), nullable=True, comment="기록 시점 IP")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    staff       = relationship("Staff", foreign_keys=[staff_id])
    store       = relationship("Store")
    corrector   = relationship("Staff", foreign_keys=[corrected_by])
    paired_record = relationship("StaffAttendance", remote_side=[id],
                                 foreign_keys=[paired_id])

    def __repr__(self):
        return (f"<StaffAttendance staff={self.staff_id} "
                f"date={self.work_date} type={self.att_type} "
                f"time={self.att_time}>")


class AttendanceSummary(Base):
    """
    일별 출퇴근 요약 (집계 캐시 테이블).

    매일 자동 집계 또는 퇴근 시 갱신.
    직원 관리 화면에서 월별 근태 조회 시 이 테이블 조회.
    원본은 StaffAttendance 참조.
    """
    __tablename__ = "attendance_summaries"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    staff_id  = Column(Integer, ForeignKey("staff.id"), nullable=False)
    store_id  = Column(Integer, ForeignKey("stores.id"), nullable=False)
    work_date = Column(Date, nullable=False)

    clock_in_time  = Column(DateTime(timezone=True), nullable=True, comment="첫 출근 시각")
    clock_out_time = Column(DateTime(timezone=True), nullable=True, comment="마지막 퇴근 시각")
    total_minutes  = Column(Integer, nullable=False, default=0,
                            comment="총 근무 시간 (분)")
    is_absent      = Column(Boolean, nullable=False, default=False,
                            comment="결근 여부 (스케줄 대비)")
    note           = Column(Text, nullable=True, comment="특이사항")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    staff = relationship("Staff")
    store = relationship("Store")

    @property
    def total_hours(self) -> float:
        """총 근무 시간 (시간 단위, 소수점 1자리)."""
        return round(self.total_minutes / 60, 1)

    def __repr__(self):
        return (f"<AttendanceSummary staff={self.staff_id} "
                f"date={self.work_date} total={self.total_hours}h>")
