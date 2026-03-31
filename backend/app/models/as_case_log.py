"""AS 케이스 상태 변경 이력"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, func
from app.database import Base


class AsCaseLog(Base):
    __tablename__ = "as_case_logs"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    as_case_id  = Column(Integer, ForeignKey("as_cases.id"), nullable=False)
    from_status = Column(String(20), nullable=True)
    to_status   = Column(String(20), nullable=False)
    staff_id    = Column(Integer, ForeignKey("staff.id"), nullable=True)
    memo        = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
