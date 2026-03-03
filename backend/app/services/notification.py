"""
통합 푸시 알림 — 텔레그램 + FCM 동시 발송.
매수/매도/손절/긴급정지 시 user.telegram_chat_id, user.fcm_token으로 발송.
"""

import asyncio
from typing import Optional
from loguru import logger

from app.config import settings
from app.services import telegram


def _get_firebase_app():
    """Firebase Admin 앱 초기화 (지연 로딩)."""
    try:
        import firebase_admin
        from firebase_admin import credentials
        if not firebase_admin._apps:
            cred_path = settings.GOOGLE_APPLICATION_CREDENTIALS
            if cred_path:
                cred = credentials.Certificate(cred_path)
                return firebase_admin.initialize_app(cred)
            return None
        return firebase_admin.get_app()
    except Exception as e:
        logger.warning(f"[FCM] Firebase 초기화 실패: {e}")
        return None


async def _send_fcm(fcm_token: str, title: str, body: str, data: Optional[dict] = None) -> bool:
    """FCM 푸시 발송 (동기 SDK를 스레드에서 실행)."""
    if not fcm_token or not fcm_token.strip():
        return False
    app = _get_firebase_app()
    if not app:
        return False
    try:
        from firebase_admin import messaging
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            token=fcm_token.strip(),
            android=messaging.AndroidConfig(priority="high"),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(aps=messaging.Aps(sound="default")),
                fcm_options=messaging.APNSFCMOptions(),
            ),
        )
        await asyncio.to_thread(messaging.send, message)
        return True
    except Exception as e:
        logger.warning(f"[FCM] 발송 실패: {e}")
        return False


async def send_buy_alert(
    telegram_chat_id: Optional[str],
    fcm_token: Optional[str],
    coin: str,
    price: float,
    invest_amount: float,
) -> None:
    """매수 체결 (PUSH-01) — 텔레그램 + FCM."""
    title = "🟢 매수 체결"
    body = f"{coin} {price:,.0f}원 · {invest_amount:,.0f}원"
    await asyncio.gather(
        telegram.send_buy_alert(telegram_chat_id, coin, price, invest_amount),
        _send_fcm(fcm_token or "", title, body, {"type": "buy", "coin": coin}),
    )


async def send_sell_alert(
    telegram_chat_id: Optional[str],
    fcm_token: Optional[str],
    coin: str,
    price: float,
    pnl_amount: float,
    pnl_pct: float,
    reason: str = "",
) -> None:
    """매도 체결 (PUSH-02) — 텔레그램 + FCM."""
    sign = "+" if pnl_amount >= 0 else ""
    title = "🔴 매도 체결" if pnl_amount < 0 else "🟢 매도 체결"
    body = f"{coin} {sign}{pnl_amount:,.0f}원 ({sign}{pnl_pct:.1f}%)"
    await asyncio.gather(
        telegram.send_sell_alert(telegram_chat_id, coin, price, pnl_amount, pnl_pct, reason),
        _send_fcm(fcm_token or "", title, body, {"type": "sell", "coin": coin}),
    )


async def send_stop_loss_alert(
    telegram_chat_id: Optional[str],
    fcm_token: Optional[str],
    coin: str,
    pnl_amount: float,
    pnl_pct: float,
) -> None:
    """손절 (PUSH-03) — 텔레그램 + FCM."""
    title = "🔴 손절"
    body = f"{coin} {pnl_amount:,.0f}원 ({pnl_pct:.1f}%)"
    await asyncio.gather(
        telegram.send_stop_loss_alert(telegram_chat_id, coin, pnl_amount, pnl_pct),
        _send_fcm(fcm_token or "", title, body, {"type": "stop_loss", "coin": coin}),
    )


async def send_emergency_stop_alert(
    telegram_chat_id: Optional[str],
    fcm_token: Optional[str],
    reason: str = "API 오류 등",
) -> None:
    """긴급 정지 (PUSH-04) — 텔레그램 + FCM."""
    title = "⚠️ 긴급 정지"
    body = reason[:100] if reason else "봇이 긴급 정지되었습니다."
    await asyncio.gather(
        telegram.send_emergency_stop_alert(telegram_chat_id, reason),
        _send_fcm(fcm_token or "", title, body, {"type": "emergency_stop"}),
    )


async def send_bot_start_alert(
    telegram_chat_id: Optional[str],
    fcm_token: Optional[str],
    krw_balance: float = 0,
) -> None:
    """봇 시작 — 텔레그램 + FCM."""
    title = "✅ 봇 시작"
    body = f"업비트 연동 확인 · KRW {krw_balance:,.0f}원"
    await asyncio.gather(
        telegram.send_bot_start_alert(telegram_chat_id, krw_balance),
        _send_fcm(fcm_token or "", title, body, {"type": "bot_start"}),
    )


async def send_bot_stop_alert(
    telegram_chat_id: Optional[str],
    fcm_token: Optional[str],
) -> None:
    """봇 정지 — 텔레그램 + FCM."""
    title = "⏹ 봇 정지"
    body = "봇이 정지되었습니다."
    await asyncio.gather(
        telegram.send_bot_stop_alert(telegram_chat_id),
        _send_fcm(fcm_token or "", title, body, {"type": "bot_stop"}),
    )
