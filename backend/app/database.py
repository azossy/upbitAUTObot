"""
SQLite 비동기 DB 연결
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    from app.models import email_verification  # noqa: F401 — 테이블 생성용
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # 기존 DB에 프로필/언어 컬럼 추가 (이미 있으면 무시)
        from sqlalchemy import text
        for col, defn in [
            ("avatar_url", "VARCHAR(512)"),
            ("preferred_language", "VARCHAR(10)"),
            ("google_id", "VARCHAR(128)"),
            ("kakao_id", "VARCHAR(128)"),
            ("fcm_token", "VARCHAR(512)"),
        ]:
            try:
                await conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {defn}"))
            except Exception:
                pass
