"""AS 케이스 + 대여기기 모델"""
from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class AsStatus(str, enum.Enum):
    접수      = "접수"
    점검중    = "점검중"
    제조사전달 = "제조사전달"
    수리완료  = "수리완료"
    반환완료  = "반환완료"
    반려      = "반려"


class AsCase(Base):
    __tablename__ = "as_cases"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    case_number = Column(String(20), nullable=False, unique=True,
                         comment="AS 번호. 예: AS-250315-001")

    customer_id      = Column(Integer, ForeignKey("customers.id"), nullable=False)
    device_id        = Column(Integer, ForeignKey("device_ledgers.id"), nullable=True)
    staff_id         = Column(Integer, ForeignKey("staff.id"), nullable=False)
    loaner_device_id = Column(Integer, ForeignKey("loaner_devices.id"), nullable=True)

    symptom    = Column(Text, nullable=False)
    status     = Column(Enum(AsStatus), nullable=False, default=AsStatus.접수)
    diagnosis  = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)

    received_at  = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    returned_at  = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())

    customer      = relationship("Customer", back_populates="as_cases")
    device        = relationship("DeviceLedger", foreign_keys=[device_id])
    staff         = relationship("Staff", foreign_keys=[staff_id])
    loaner_device = relationship("LoanerDevice", foreign_keys=[loaner_device_id])

    def __repr__(self):
        return f"<AsCase {self.case_number} status={self.status}>"


class LoanerStatus(str, enum.Enum):
    대여가능 = "대여가능"
    대여중   = "대여중"
    회수완료 = "회수완료"
    미회수   = "미회수"
    수리중   = "수리중"
    폐기     = "폐기"


class LoanerDevice(Base):
    __tablename__ = "loaner_devices"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    device_name = Column(String(200), nullable=False)
    device_memo = Column(Text, nullable=True)
    status      = Column(Enum(LoanerStatus), nullable=False, default=LoanerStatus.대여가능)

    current_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    current_as_case_id  = Column(Integer, ForeignKey("as_cases.id"), nullable=True)
    loaned_at           = Column(DateTime(timezone=True), nullable=True,
                                 comment="대여 시작일. 회수예정일 없음, 수동 관리")
    loaned_by           = Column(Integer, ForeignKey("staff.id"), nullable=True)
    returned_at         = Column(DateTime(timezone=True), nullable=True)
    returned_to         = Column(Integer, ForeignKey("staff.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    current_customer  = relationship("Customer", foreign_keys=[current_customer_id])
    current_as_case   = relationship("AsCase", foreign_keys=[current_as_case_id])
    loaned_by_staff   = relationship("Staff", foreign_keys=[loaned_by])
    returned_to_staff = relationship("Staff", foreign_keys=[returned_to])

    def __repr__(self):
        return f"<LoanerDevice id={self.id} name={self.device_name} status={self.status}>"
