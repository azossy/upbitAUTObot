"""보유 포지션 모델"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    coin = Column(String(20), nullable=False)
    avg_entry_price = Column(Float, nullable=False)
    total_quantity = Column(Float, nullable=False)
    total_invested = Column(Float, nullable=False)
    stop_loss_price = Column(Float, nullable=True)
    trailing_stop_active = Column(Boolean, default=False)
    highest_price = Column(Float, nullable=True)
    tp1_filled = Column(Boolean, default=False)
    tp2_filled = Column(Boolean, default=False)
    tp3_filled = Column(Boolean, default=False)
    opened_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="positions")
