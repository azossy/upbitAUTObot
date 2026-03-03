"""인증 API"""
import secrets
from pathlib import Path
from datetime import datetime, timedelta, timezone
from math import ceil
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import httpx

from app.database import get_db
from app.models.user import User, UserRole
from app.models.email_verification import EmailVerification
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    GoogleLoginRequest,
    KakaoLoginRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    TokenResponse,
    UserResponse,
    MessageResponse,
    FcmTokenRequest,
    SendVerificationEmailRequest,
    VerifyAndRegisterRequest,
)
from app.services.email_service import (
    is_smtp_configured,
    send_verification_email,
    send_welcome_email,
)
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
)
from app.middleware.auth_middleware import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["인증"])

# 프로필 사진 저장 경로 (앱에서 직접 저장)
_BASE_DIR = Path(__file__).resolve().parent.parent.parent
AVATAR_DIR = _BASE_DIR / "static" / "avatars"
AVATAR_MAX_BYTES = 5 * 1024 * 1024  # 5MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/jpg"}

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


@router.post("/register", response_model=MessageResponse, status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """기존 회원가입 (인증 없이). 앱에서는 인증 플로우(verify-and-register) 사용 권장."""
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="이미 등록된 이메일")
    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        nickname=req.nickname,
        role=UserRole.USER,
    )
    db.add(user)
    await db.commit()
    return MessageResponse(message="회원가입 완료")


@router.post("/send-verification-email", response_model=MessageResponse)
async def send_verification_email_endpoint(
    req: SendVerificationEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    """회원가입 인증용 6자리 코드를 이메일로 발송. SMTP 설정 필요."""
    if not is_smtp_configured():
        raise HTTPException(
            status_code=503,
            detail="이메일 발송이 설정되지 않았습니다. 서버 관리자에게 문의하세요.",
        )
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")
    code = "".join(secrets.choice("0123456789") for _ in range(6))
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    expires_at = now_utc + timedelta(minutes=settings.VERIFICATION_CODE_EXPIRE_MINUTES)
    await db.execute(delete(EmailVerification).where(EmailVerification.email == req.email))
    db.add(EmailVerification(email=req.email, code=code, expires_at=expires_at))
    await db.commit()
    if not send_verification_email(req.email, code):
        raise HTTPException(status_code=503, detail="이메일 발송에 실패했습니다. 잠시 후 다시 시도해 주세요.")
    return MessageResponse(message="인증 메일을 발송했습니다. 메일함을 확인해 주세요.")


@router.post("/verify-and-register", response_model=MessageResponse, status_code=201)
async def verify_and_register(
    req: VerifyAndRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """이메일 인증 코드 확인 후 회원가입 완료. 축하 메일 발송 후 로그인 화면으로."""
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")
    result = await db.execute(
        select(EmailVerification)
        .where(EmailVerification.email == req.email)
        .order_by(EmailVerification.expires_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    if not row or row.expires_at < now_utc:
        raise HTTPException(status_code=400, detail="인증 번호가 만료되었거나 일치하지 않습니다. 인증 메일을 다시 요청해 주세요.")
    if row.code != req.code.strip():
        raise HTTPException(status_code=400, detail="인증 번호가 일치하지 않습니다.")
    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        nickname=req.nickname,
        role=UserRole.USER,
    )
    db.add(user)
    await db.execute(delete(EmailVerification).where(EmailVerification.email == req.email))
    await db.commit()
    send_welcome_email(req.email, req.nickname)
    return MessageResponse(message="회원가입이 완료되었습니다. 로그인해 주세요.")


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호 오류")
    # DB는 naive UTC 저장 → 비교·설정 시 naive로 통일 (Python 3.12+ utcnow 대체)
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    if user.locked_until and user.locked_until > now_utc:
        remaining = max(0, ceil((user.locked_until - now_utc).total_seconds() / 60))
        return JSONResponse(
            status_code=403,
            content={
                "detail": "계정이 일시 잠금되었습니다.",
                "remaining_minutes": int(remaining),
            },
        )
    if not verify_password(req.password, user.password_hash):
        user.login_fail_count = (user.login_fail_count or 0) + 1
        if user.login_fail_count >= MAX_LOGIN_ATTEMPTS:
            user.locked_until = now_utc + timedelta(minutes=LOCKOUT_MINUTES)
        await db.commit()
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호 오류")
    user.login_fail_count = 0
    user.locked_until = None
    await db.commit()
    token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname,
            "role": user.role.value,
        },
    )


def _make_token_response(user: User):
    token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname,
            "role": user.role.value,
        },
    )


@router.post("/google", response_model=TokenResponse)
async def login_google(
    req: GoogleLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """구글 로그인. id_token 검증 후 사용자 생성/조회하여 JWT 반환."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="구글 로그인이 설정되지 않았습니다.")
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        id_info = id_token.verify_oauth2_token(
            req.id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except Exception:
        raise HTTPException(status_code=401, detail="구글 토큰 검증에 실패했습니다.")
    google_id = str(id_info.get("sub", ""))
    email = id_info.get("email") or f"google_{google_id}@oauth.local"
    name = id_info.get("name") or email.split("@")[0]
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()
    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.google_id = google_id
            await db.commit()
            await db.refresh(user)
        else:
            user = User(
                email=email,
                password_hash=hash_password(google_id + "_oauth_placeholder"),
                nickname=name[:100],
                role=UserRole.USER,
                google_id=google_id,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
    return _make_token_response(user)


@router.post("/kakao", response_model=TokenResponse)
async def login_kakao(
    req: KakaoLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """카카오 로그인. access_token으로 사용자 정보 조회 후 JWT 반환."""
    if not settings.KAKAO_REST_API_KEY:
        raise HTTPException(status_code=503, detail="카카오 로그인이 설정되지 않았습니다.")
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {req.access_token}"},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="카카오 토큰 검증에 실패했습니다.")
    data = r.json()
    kakao_id = str(data.get("id", ""))
    kakao_account = data.get("kakao_account") or {}
    email = kakao_account.get("email") or f"kakao_{kakao_id}@oauth.local"
    profile = kakao_account.get("profile") or {}
    name = profile.get("nickname") or email.split("@")[0]
    result = await db.execute(select(User).where(User.kakao_id == kakao_id))
    user = result.scalar_one_or_none()
    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.kakao_id = kakao_id
            await db.commit()
            await db.refresh(user)
        else:
            user = User(
                email=email,
                password_hash=hash_password(kakao_id + "_oauth_placeholder"),
                nickname=name[:100],
                role=UserRole.USER,
                kakao_id=kakao_id,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
    return _make_token_response(user)


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        role=user.role.value,
        telegram_chat_id=user.telegram_chat_id,
        avatar_url=user.avatar_url,
        preferred_language=user.preferred_language,
    )


@router.get("/profile", response_model=UserResponse)
async def get_profile(user: User = Depends(get_current_user)):
    """프로필 조회 (이메일, 별명, 프로필 사진 URL, 선호 언어)."""
    return UserResponse(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        role=user.role.value,
        telegram_chat_id=user.telegram_chat_id,
        avatar_url=user.avatar_url,
        preferred_language=user.preferred_language,
    )


@router.post("/profile/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """프로필 사진 업로드. 카메라/앨범에서 선택한 이미지를 앱 서버에 저장."""
    content_type = (file.content_type or "").strip().lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="JPEG 또는 PNG 이미지만 업로드 가능합니다.",
        )
    body = await file.read()
    if len(body) > AVATAR_MAX_BYTES:
        raise HTTPException(status_code=400, detail="파일 크기는 5MB 이하여야 합니다.")
    ext = ".png" if "png" in content_type else ".jpg"
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    path = AVATAR_DIR / f"{user.id}{ext}"
    path.write_bytes(body)
    avatar_url = f"/static/avatars/{user.id}{ext}"
    user.avatar_url = avatar_url
    await db.commit()
    await db.refresh(user)
    return UserResponse(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        role=user.role.value,
        telegram_chat_id=user.telegram_chat_id,
        avatar_url=user.avatar_url,
        preferred_language=user.preferred_language,
    )


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    req: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """프로필 수정 (별명, 프로필 사진 URL, 선호 언어)."""
    if req.nickname is not None:
        user.nickname = req.nickname.strip()
    if req.avatar_url is not None:
        user.avatar_url = req.avatar_url.strip() or None
    if req.preferred_language is not None:
        user.preferred_language = req.preferred_language.strip() or None
    await db.commit()
    await db.refresh(user)
    return UserResponse(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        role=user.role.value,
        telegram_chat_id=user.telegram_chat_id,
        avatar_url=user.avatar_url,
        preferred_language=user.preferred_language,
    )


@router.put("/me/fcm-token", response_model=MessageResponse)
async def register_fcm_token(
    req: FcmTokenRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """FCM 토큰 등록/해제. 로그인 후 앱에서 호출."""
    user.fcm_token = (req.fcm_token or "").strip() or None
    await db.commit()
    return MessageResponse(message="FCM 토큰이 등록되었습니다." if user.fcm_token else "FCM 토큰이 해제되었습니다.")


@router.put("/password", response_model=MessageResponse)
async def change_password(
    req: PasswordChangeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """비밀번호 변경. JWT 인증 필수. 현재 비밀번호 확인 후 새 비밀번호로 갱신."""
    if not verify_password(req.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="현재 비밀번호가 일치하지 않습니다.")
    user.password_hash = hash_password(req.new_password)
    await db.commit()
    return MessageResponse(message="비밀번호가 변경되었습니다.")
