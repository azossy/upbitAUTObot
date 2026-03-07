"""
트레이딩 엔진 — 봇 시작 시 업비트 API 검증용 백그라운드 루프.
- 종목: Bot.config["coin_select_mode"] (auto|manual), Bot.config["selected_markets"] (수동 시 최대 10종목).
- Bot.config["allocation_strategy"]: profit_first | loss_min | balanced | engine_decision
  - 수익성우선(profit_first): 상승 점수에 비례·상위 편중 배분(score^1.5).
  - 손실최소(loss_min): 균등 배분으로 리스크 분산.
  - 균형(balanced): 균등 배분.
  - 개미엔진판단(engine_decision): 엔진 점수 그대로 비율 배분.
"""


def allocate_krw_by_scores(
    total_krw: float,
    market_scores: list[tuple[str, float]],
    min_per_market: float = 5000.0,
) -> dict[str, float]:
    """
    여러 종목에 투자금을 점수 비율로 분배. (상승 가능성 백분율에 따른 분산 매수)
    market_scores: [(market, score), ...], score는 0 이상. 0이면 해당 종목 제외.
    반환: { market: krw_amount, ... }
    """
    if not market_scores or total_krw < min_per_market:
        return {}
    eligible = [(m, max(0.0, s)) for m, s in market_scores if max(0.0, s) > 0]
    if not eligible:
        return {}
    total_score = sum(s for _, s in eligible)
    if total_score <= 0:
        return {}
    out = {}
    for market, score in eligible:
        krw = total_krw * (score / total_score)
        if krw >= min_per_market:
            out[market] = round(krw, 0)
    return out


def allocate_by_strategy(
    total_krw: float,
    market_scores: list[tuple[str, float]],
    strategy: str,
    min_per_market: float = 5000.0,
) -> dict[str, float]:
    """
    투자 전략에 따라 총 투자금을 종목별로 분배.
    - profit_first: 수익성 우선 — 점수^1.5 비율(상위 종목 편중).
    - loss_min: 손실 최소 — 균등 배분.
    - balanced: 균형 — 균등 배분.
    - engine_decision: 개미엔진 판단 — 점수 그대로 비율 배분(기본 allocate_krw_by_scores).
    """
    if not market_scores or total_krw < min_per_market:
        return {}
    eligible = [(m, max(0.0, s)) for m, s in market_scores if m]
    if not eligible:
        return {}

    if strategy == "profit_first":
        # 상위 종목에 더 쏠리도록 가중치 = score^1.5
        weighted = [(m, (s + 0.1) ** 1.5) for m, s in eligible]
        total_w = sum(w for _, w in weighted)
        if total_w <= 0:
            return {}
        out = {}
        for (market, w) in weighted:
            krw = total_krw * (w / total_w)
            if krw >= min_per_market:
                out[market] = round(krw, 0)
        return out

    if strategy in ("loss_min", "balanced"):
        # 균등 배분
        n = len(eligible)
        krw_each = total_krw / n
        if krw_each < min_per_market:
            return {}
        return {m: round(krw_each, 0) for m, _ in eligible}

    # engine_decision 또는 기본
    return allocate_krw_by_scores(total_krw, market_scores, min_per_market)

import asyncio
from loguru import logger

from app.database import AsyncSessionLocal
from app.models.bot import Bot, BotStatus
from app.models.api_key import ApiKey
from app.models.user import User
from app.utils.encryption import decrypt_api_key
from app.trading.upbit_client import UpbitClient
from sqlalchemy import select
from sqlalchemy.orm import joinedload


async def trading_loop(app, user_id: int):
    """
    봇이 RUNNING인 동안 주기적으로 업비트 API(잔고 조회)를 호출하는 검증용 루프.
    봇 정지 시 외부에서 task.cancel() 호출되면 종료됩니다.
    Bot 조회 시 User를 joinedload로 함께 로드해 알림 시 별도 User 쿼리 제거.
    """
    sent_start_alert = False
    try:
        while True:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Bot).where(Bot.user_id == user_id).options(joinedload(Bot.user))
                )
                bot = result.scalar_one_or_none()
                if not bot or bot.status != BotStatus.RUNNING:
                    logger.info(f"[트레이딩] user_id={user_id} 봇이 RUNNING이 아님 — 루프 종료")
                    break

                key_result = await session.execute(
                    select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.is_active == True)
                )
                api_key = key_result.scalar_one_or_none()
                if not api_key:
                    logger.warning(f"[트레이딩] user_id={user_id} 활성 API 키 없음")
                    await asyncio.sleep(30)
                    continue

                try:
                    access_key = decrypt_api_key(api_key.encrypted_api_key)
                    secret_key = decrypt_api_key(api_key.encrypted_api_secret)
                except Exception as e:
                    logger.error(f"[트레이딩] user_id={user_id} API 키 복호화 실패: {e}")
                    await asyncio.sleep(60)
                    continue

                user = bot.user
                client = UpbitClient(access_key, secret_key)
                try:
                    accounts = await client.get_accounts()
                    krw = await client.get_krw_balance()
                    logger.info(f"[트레이딩] user_id={user_id} 업비트 API 연동 확인 — 잔고 조회 성공, KRW={krw:,.0f}")
                    if not sent_start_alert and user and (user.telegram_chat_id or user.fcm_token):
                        sent_start_alert = True
                        from app.services.notification import send_bot_start_alert
                        await send_bot_start_alert(user.telegram_chat_id, user.fcm_token, krw)
                except Exception as e:
                    logger.warning(f"[트레이딩] user_id={user_id} 업비트 API 호출 실패: {e}")
                    bot.status = BotStatus.STOPPED
                    await session.commit()
                    if user and (user.telegram_chat_id or user.fcm_token):
                        from app.services.notification import send_emergency_stop_alert
                        await send_emergency_stop_alert(user.telegram_chat_id, user.fcm_token, str(e))
                    break

            await asyncio.sleep(60)
    except asyncio.CancelledError:
        logger.info(f"[트레이딩] user_id={user_id} 봇 정지로 루프 취소됨")
        async with AsyncSessionLocal() as session:
            user_result = await session.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            if user and (user.telegram_chat_id or user.fcm_token):
                from app.services.notification import send_bot_stop_alert
                await send_bot_stop_alert(user.telegram_chat_id, user.fcm_token)
    except Exception as e:
        logger.exception(f"[트레이딩] user_id={user_id} 루프 예외: {e}")
