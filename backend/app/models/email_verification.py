"""이메일 인증 코드 저장 (회원가입 인증용)"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), nullable=False, index=True)
    code = Column(String(10), nullable=False)
    expires_at = Column(DateTime, nullable=False)
