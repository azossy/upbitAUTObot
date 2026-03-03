"""
환경 변수 설정 — Pydantic Settings
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # DB: SQLite
    DATABASE_URL: str = "sqlite+aiosqlite:///./upbit_trading.db"

    # JWT
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_64_CHARS_HEX"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # API 키 암호화 (64자 hex)
    ENCRYPTION_KEY: str = "0" * 64

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    # OAuth (구글·카카오 로그인)
    GOOGLE_CLIENT_ID: str = ""
    KAKAO_REST_API_KEY: str = ""

    # 텔레그램
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_DEFAULT_CHAT_ID: str = ""

    # FCM (Firebase Cloud Messaging) — 서비스 계정 JSON 경로
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # 서버
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
