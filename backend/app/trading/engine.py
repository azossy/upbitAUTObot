"""
트레이딩 엔진 — 봇 시작 시 업비트 API 검증용 백그라운드 루프.
- 검증 모드: 실제 주문 없이 잔고 조회(get_accounts)만 수행. 로그에 "업비트 API 연동 확인" 기록.
- 봇 정지 시 asyncio 태스크 취소, 정상 종료. 미체결 주문 취소는 실제 주문 로직 도입 후 적용.
- 실제 매매는 추후 전략·주문 로직 이식 후 동작하며, 사용자 책임으로 안내합니다.
"""

import asyncio
from loguru import logger

from app.database import AsyncSessionLocal
from app.models.bot import Bot, BotStatus
from app.models.api_key import ApiKey
from app.models.user import User
from app.utils.encryption import decrypt_api_key
from app.trading.upbit_client import UpbitClient
from sqlalchemy import select


async def trading_loop(app, user_id: int):
    """
    봇이 RUNNING인 동안 주기적으로 업비트 API(잔고 조회)를 호출하는 검증용 루프.
    봇 정지 시 외부에서 task.cancel() 호출되면 종료됩니다.
    """
    sent_start_alert = False
    try:
        while True:
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(Bot).where(Bot.user_id == user_id))
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

                client = UpbitClient(access_key, secret_key)
                try:
                    accounts = await client.get_accounts()
                    krw = await client.get_krw_balance()
                    logger.info(f"[트레이딩] user_id={user_id} 업비트 API 연동 확인 — 잔고 조회 성공, KRW={krw:,.0f}")
                    if not sent_start_alert:
                        sent_start_alert = True
                        user_result = await session.execute(select(User).where(User.id == user_id))
                        user = user_result.scalar_one_or_none()
                        if user and (user.telegram_chat_id or user.fcm_token):
                            from app.services.notification import send_bot_start_alert
                            await send_bot_start_alert(user.telegram_chat_id, user.fcm_token, krw)
                except Exception as e:
                    logger.warning(f"[트레이딩] user_id={user_id} 업비트 API 호출 실패: {e}")
                    bot.status = BotStatus.STOPPED
                    await session.commit()
                    user_result = await session.execute(select(User).where(User.id == user_id))
                    user = user_result.scalar_one_or_none()
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
