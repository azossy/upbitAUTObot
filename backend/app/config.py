"""
환경 변수 설정 — Pydantic Settings
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # DB: SQLite
    DATABASE_URL: str = "sqlite+aiosqlite:///./baejjangi.db"

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

    # 이메일 발송 (회원가입 인증·축하 메일)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "배짱이 <noreply@example.com>"
    VERIFICATION_CODE_EXPIRE_MINUTES: int = 1
    # 문의용 기본 메일 (발송 메일 하단 안내)
    APP_CONTACT_EMAIL: str = "baejjangi@example.com"

    # 서버
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # .env에만 있고 여기 없는 변수는 무시(구버전 배포 시 기동 실패 방지)


settings = Settings()
