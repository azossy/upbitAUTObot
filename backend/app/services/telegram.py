"""
텔레그램 푸시 알림 (매수/매도/손절/긴급정지).
TELEGRAM_BOT_TOKEN 환경변수, 사용자별 chat_id(DB user.telegram_chat_id) 사용.
chat_id 없으면 발송 건너뜀.
"""

from typing import Optional
from datetime import datetime
import httpx
from loguru import logger

from app.config import settings

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


async def _send(chat_id: str, text: str) -> bool:
    if not settings.TELEGRAM_BOT_TOKEN or not chat_id or not chat_id.strip():
        return False
    url = TELEGRAM_API.format(token=settings.TELEGRAM_BOT_TOKEN)
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                url,
                json={"chat_id": chat_id.strip(), "text": text, "parse_mode": "HTML"},
                timeout=10.0,
            )
            if r.status_code != 200:
                logger.warning(f"[텔레그램] 발송 실패 chat_id={chat_id[:8]}... status={r.status_code}")
                return False
            return True
    except Exception as e:
        logger.warning(f"[텔레그램] 발송 예외: {e}")
        return False


async def send_buy_alert(chat_id: Optional[str], coin: str, price: float, invest_amount: float) -> bool:
    """매수 체결 (PUSH-01)"""
    msg = (
        f"🟢 <b>매수 체결</b>\n"
        f"코인: <code>{coin}</code>\n"
        f"가격: <code>{price:,.0f}</code>원\n"
        f"투자금: <code>{invest_amount:,.0f}</code>원\n"
        f"⏰ {datetime.now().strftime('%H:%M:%S')}"
    )
    return await _send(chat_id or "", msg)


async def send_sell_alert(
    chat_id: Optional[str],
    coin: str,
    price: float,
    pnl_amount: float,
    pnl_pct: float,
    reason: str = "",
) -> bool:
    """매도 체결 (PUSH-02)"""
    emoji = "🔴" if pnl_amount < 0 else "🟢"
    sign = "+" if pnl_amount >= 0 else ""
    msg = (
        f"{emoji} <b>매도 체결</b>\n"
        f"코인: <code>{coin}</code>\n"
        f"가격: <code>{price:,.0f}</code>원\n"
        f"손익: <code>{sign}{pnl_amount:,.0f}</code>원 ({sign}{pnl_pct:.1f}%)\n"
        f"사유: {reason or '-'}\n"
        f"⏰ {datetime.now().strftime('%H:%M:%S')}"
    )
    return await _send(chat_id or "", msg)


async def send_stop_loss_alert(chat_id: Optional[str], coin: str, pnl_amount: float, pnl_pct: float) -> bool:
    """손절 (PUSH-03)"""
    msg = (
        f"🔴 <b>손절</b>\n"
        f"코인: <code>{coin}</code>\n"
        f"손실: <code>{pnl_amount:,.0f}</code>원 ({pnl_pct:.1f}%)\n"
        f"⏰ {datetime.now().strftime('%H:%M:%S')}"
    )
    return await _send(chat_id or "", msg)


async def send_emergency_stop_alert(chat_id: Optional[str], reason: str = "API 오류 등") -> bool:
    """긴급 정지 (PUSH-04)"""
    msg = (
        f"⚠️ <b>긴급 정지</b>\n"
        f"사유: {reason}\n"
        f"⏰ {datetime.now().strftime('%H:%M:%S')}"
    )
    return await _send(chat_id or "", msg)


async def send_bot_start_alert(chat_id: Optional[str], krw_balance: float = 0) -> bool:
    """봇 시작·업비트 연동 확인 알림"""
    msg = (
        f"✅ <b>봇이 시작되었습니다</b>\n"
        f"업비트 API 연동 확인됨.\n"
        f"KRW 잔고: <code>{krw_balance:,.0f}</code>원\n"
        f"⏰ {datetime.now().strftime('%H:%M:%S')}"
    )
    return await _send(chat_id or "", msg)


async def send_bot_stop_alert(chat_id: Optional[str]) -> bool:
    """봇 정지 알림"""
    msg = (
        f"⏹ <b>봇이 정지되었습니다</b>\n"
        f"⏰ {datetime.now().strftime('%H:%M:%S')}"
    )
    return await _send(chat_id or "", msg)
