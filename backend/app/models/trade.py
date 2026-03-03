"""거래 내역 모델"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from app.database import Base


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    coin = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # bid, ask
    reason = Column(String(50), nullable=True)
    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    fee = Column(Float, default=0.0)
    realized_pnl = Column(Float, nullable=True)
    realized_pnl_pct = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="trades")
