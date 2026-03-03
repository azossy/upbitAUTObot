"""인증/봇 스키마"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# 비밀번호 최소 길이 (상용 프로그램 수준)
MIN_PASSWORD_LENGTH = 8


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, description="비밀번호 8자 이상")
    nickname: str = Field(..., min_length=1, max_length=100, description="닉네임 1~100자")


class SendVerificationEmailRequest(BaseModel):
    email: EmailStr = Field(..., description="인증 메일을 받을 이메일")


class VerifyAndRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, description="비밀번호 8자 이상")
    nickname: str = Field(..., min_length=1, max_length=100, description="닉네임 1~100자")
    code: str = Field(..., min_length=4, max_length=10, description="이메일로 받은 인증 번호")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, description="비밀번호 필수")


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(..., min_length=1, description="Google ID Token")


class KakaoLoginRequest(BaseModel):
    access_token: str = Field(..., min_length=1, description="Kakao Access Token")


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1, description="현재 비밀번호")
    new_password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, description="새 비밀번호 8자 이상")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserResponse(BaseModel):
    id: int
    email: str
    nickname: str
    role: str
    telegram_chat_id: Optional[str] = None
    avatar_url: Optional[str] = None
    preferred_language: Optional[str] = None

    class Config:
        from_attributes = True


class ProfileUpdateRequest(BaseModel):
    nickname: Optional[str] = Field(None, min_length=1, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=512)
    preferred_language: Optional[str] = Field(None, max_length=10)


class MessageResponse(BaseModel):
    message: str


class FcmTokenRequest(BaseModel):
    fcm_token: Optional[str] = Field(None, max_length=512, description="FCM 토큰 (빈 문자열이면 등록 해제)")


class BotConfigRequest(BaseModel):
    max_investment_ratio: Optional[float] = Field(None, ge=0, le=1, description="0~1")
    max_positions: Optional[int] = Field(None, ge=1, le=20, description="1~20")
    stop_loss_pct: Optional[float] = Field(None, ge=0, le=100, description="0~100%")
    take_profit_pct: Optional[float] = Field(None, ge=0, le=100, description="0~100%")
    telegram_chat_id: Optional[str] = None


class BotStatusResponse(BaseModel):
    status: str
    market_mode: str
    market_score: int
    total_pnl: float
    win_rate: float
    daily_pnl: float
    weekly_pnl: float


class ApiKeyCreateRequest(BaseModel):
    access_key: str
    secret_key: str
    label: Optional[str] = None


class ApiKeyResponse(BaseModel):
    id: int
    exchange: str
    label: Optional[str]
    masked_key: str
    is_active: bool

    class Config:
        from_attributes = True
