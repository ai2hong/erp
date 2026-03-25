"""
models/auth.py — 인증 보조 모델

StaffRegistrationRequest  가입 신청 대기 테이블
LoginHistory              로그인 성공·실패 이력  ← 선택 옵션
StaffSession              Refresh 토큰 세션 (1계정 1기기 보장)  ← 선택 옵션
TokenBlacklist            로그아웃된 토큰 JTI 목록
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, Enum,
    DateTime, Text, ForeignKey, UniqueConstraint, func,
)
from sqlalchemy.orm import relationship
from app.database import Base
import enum


# ══════════════════════════════════════════════
# 가입 신청
# ══════════════════════════════════════════════

class RegistrationStatus(str, enum.Enum):
    대기 = "대기"   # 승인 전
    승인 = "승인"   # Staff 레코드 생성 완료
    반려 = "반려"   # 거부


class StaffRegistrationRequest(Base):
    """
    직원이 제출하는 가입 신청서.
    사장·총괄 승인 시 Staff 레코드 자동 생성 후 status → 승인.

    보안 노트:
      - hashed_password: 신청 시 bcrypt 해싱 저장, 평문은 즉시 파기
      - 반려 시 hashed_password 를 빈 문자열로 덮어씀 (개인정보 최소화)
      - login_id: staff 테이블 + 신청 테이블 양쪽 모두 중복 검사
    """
    __tablename__ = "staff_registration_requests"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    name             = Column(String(50),  nullable=False)
    login_id         = Column(String(50),  nullable=False, unique=True)
    hashed_password  = Column(String(200), nullable=False,
                              comment="신청 시 bcrypt 해싱. 반려 시 삭제.")
    store_id         = Column(Integer, ForeignKey("stores.id"), nullable=False)
    memo             = Column(Text, nullable=True, comment="신청자 메모 (선택)")

    status           = Column(Enum(RegistrationStatus), nullable=False,
                              default=RegistrationStatus.대기)
    reviewed_by      = Column(Integer, ForeignKey("staff.id"), nullable=True)
    rejected_reason  = Column(Text, nullable=True)
    reviewed_at      = Column(DateTime(timezone=True), nullable=True)
    created_staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    store         = relationship("Store")
    reviewer      = relationship("Staff", foreign_keys=[reviewed_by])
    created_staff = relationship("Staff", foreign_keys=[created_staff_id])

    def __repr__(self):
        return f"<RegistrationRequest {self.login_id} status={self.status}>"


# ══════════════════════════════════════════════
# 로그인 이력  ← 선택 옵션
# ══════════════════════════════════════════════

class LoginResult(str, enum.Enum):
    성공         = "성공"
    실패         = "실패"
    강제로그아웃  = "강제로그아웃"   # 다른 기기 로그인으로 세션 만료


class LoginHistory(Base):
    """
    모든 로그인 시도 이력.

    저장 목적:
      - 운영자가 언제 누가 어디서 로그인했는지 확인
      - 이상 접근(낯선 IP) 사후 감지
      - 강제로그아웃 발생 여부 추적

    staff_id 는 성공 시에만 기록 (실패는 login_id 만 저장).
    """
    __tablename__ = "login_histories"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    staff_id   = Column(Integer, ForeignKey("staff.id"), nullable=True)
    login_id   = Column(String(50), nullable=False, comment="시도한 login_id")
    result     = Column(Enum(LoginResult), nullable=False)
    ip_address = Column(String(45),  nullable=True, comment="IPv4 / IPv6")
    user_agent = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    staff = relationship("Staff", foreign_keys=[staff_id])

    def __repr__(self):
        return f"<LoginHistory {self.login_id} result={self.result}>"


# ══════════════════════════════════════════════
# 활성 세션  ← 선택 옵션 (1계정 1기기 보장)
# ══════════════════════════════════════════════

class StaffSession(Base):
    """
    로그인 시 Refresh 토큰 JTI를 등록.
    UniqueConstraint("staff_id") → 계정당 세션 1개만 허용.

    동작:
      새 기기로 로그인 → 기존 세션 JTI 블랙리스트 등록
                       → LoginHistory에 강제로그아웃 기록
                       → 새 세션으로 교체

    Refresh 갱신(rotate) 시: refresh_jti 만 업데이트.
    로그아웃 시: 세션 삭제 + TokenBlacklist 에 JTI 등록.
    """
    __tablename__ = "staff_sessions"
    __table_args__ = (
        UniqueConstraint("staff_id", name="uq_one_session_per_staff"),
    )

    id           = Column(Integer, primary_key=True, autoincrement=True)
    staff_id     = Column(Integer, ForeignKey("staff.id"), nullable=False, unique=True)
    refresh_jti  = Column(String(64), nullable=False, unique=True,
                          comment="현재 유효한 Refresh 토큰의 JTI")
    ip_address   = Column(String(45),  nullable=True)
    user_agent   = Column(String(512), nullable=True)
    logged_in_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at   = Column(DateTime(timezone=True), nullable=False)
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())

    staff = relationship("Staff")

    def __repr__(self):
        return f"<StaffSession staff={self.staff_id} jti={self.refresh_jti[:8]}…>"


# ══════════════════════════════════════════════
# 토큰 블랙리스트
# ══════════════════════════════════════════════

class TokenBlacklist(Base):
    """
    로그아웃되거나 무효화된 토큰의 JTI 목록.

    조회 순서 (Redis 있을 경우):
      Redis 캐시 → 없으면 DB 조회 (Redis 없어도 이 테이블만으로 동작)

    정리 주기:
      expires_at 이 지난 행은 정기 cron 으로 삭제 권장.
    """
    __tablename__ = "token_blacklist"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    jti        = Column(String(64), nullable=False, unique=True)
    staff_id   = Column(Integer, ForeignKey("staff.id"), nullable=True)
    token_type = Column(String(10), nullable=False, comment="access | refresh")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    staff = relationship("Staff")

    def __repr__(self):
        return f"<TokenBlacklist jti={self.jti[:8]}… type={self.token_type}>"
