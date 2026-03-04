"""봇 모델"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, JSON, Float
from sqlalchemy.orm import relationship
from app.database import Base


class BotStatus(str, enum.Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class MarketMode(str, enum.Enum):
    BULL = "bull"
    SIDEWAYS = "sideways"
    BEAR = "bear"
    UNKNOWN = "unknown"


class Bot(Base):
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    status = Column(Enum(BotStatus), default=BotStatus.STOPPED, nullable=False)
    market_mode = Column(Enum(MarketMode), default=MarketMode.UNKNOWN, nullable=False)
    market_score = Column(Integer, default=0)
    config = Column(JSON, default=dict)
    total_pnl = Column(Float, default=0.0)
    win_count = Column(Integer, default=0)
    loss_count = Column(Integer, default=0)
    daily_pnl = Column(Float, default=0.0)
    weekly_pnl = Column(Float, default=0.0)
    session_start_krw = Column(Float, nullable=True)  # 봇 시작 시점 원화 잔고 (재시작 시 0%부터 카운트)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="bots")
