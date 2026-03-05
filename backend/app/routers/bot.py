"""봇 API"""
import asyncio
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
import csv
import io
from sqlalchemy import select
from sqlalchemy.orm import attributes

from app.database import get_db
from app.models.user import User
from app.models.bot import Bot, BotStatus, MarketMode
from app.models.api_key import ApiKey
from app.models.position import Position
from app.models.trade import Trade
from app.schemas.auth import (
    BotStatusResponse,
    BotConfigRequest,
    StopBotRequest,
    ApiKeyCreateRequest,
    ApiKeyResponse,
    MessageResponse,
)
from app.middleware.auth_middleware import get_current_user
from app.utils.encryption import encrypt_api_key, decrypt_api_key
from app.trading.engine import trading_loop
from app.trading.upbit_client import UpbitClient

router = APIRouter(prefix="/api/v1/bot", tags=["봇"])


async def get_or_create_bot(user: User, db: AsyncSession) -> Bot:
    result = await db.execute(select(Bot).where(Bot.user_id == user.id))
    bot = result.scalar_one_or_none()
    if not bot:
        bot = Bot(user_id=user.id)
        db.add(bot)
        await db.commit()
        await db.refresh(bot)
    return bot


@router.get("/status", response_model=BotStatusResponse)
async def get_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bot = await get_or_create_bot(user, db)
    total = bot.win_count + bot.loss_count
    win_rate = (bot.win_count / total * 100) if total > 0 else 0.0
    return BotStatusResponse(
        status=bot.status.value,
        market_mode=bot.market_mode.value,
        market_score=bot.market_score,
        total_pnl=bot.total_pnl,
        win_rate=round(win_rate, 1),
        daily_pnl=bot.daily_pnl,
        weekly_pnl=bot.weekly_pnl,
        session_start_krw=getattr(bot, "session_start_krw", None),
    )


@router.post("/start", response_model=MessageResponse)
async def start_bot(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bot = await get_or_create_bot(user, db)
    result = await db.execute(select(ApiKey).where(ApiKey.user_id == user.id, ApiKey.is_active == True))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=400, detail="API 키를 먼저 등록하세요")
    tasks = getattr(request.app.state, "trading_tasks", {})
    if user.id in tasks and not tasks[user.id].done():
        raise HTTPException(status_code=400, detail="이미 봇이 실행 중입니다")
    session_start_krw = None
    try:
        access_key = decrypt_api_key(api_key.encrypted_api_key)
        secret_key = decrypt_api_key(api_key.encrypted_api_secret)
        client = UpbitClient(access_key, secret_key)
        accounts = await client.get_accounts()
        for acc in accounts:
            if acc.get("currency") == "KRW":
                session_start_krw = float(acc.get("balance", 0) or 0)
                break
    except Exception:
        pass
    bot.status = BotStatus.RUNNING
    bot.session_start_krw = session_start_krw
    await db.commit()
    task = asyncio.create_task(trading_loop(request.app, user.id))
    request.app.state.trading_tasks[user.id] = task
    return MessageResponse(message="봇이 시작되었습니다")


@router.post("/stop", response_model=MessageResponse)
async def stop_bot(
    req: StopBotRequest | None = Body(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # stop_mode: immediate(즉시) | after_sell(매각 후). 현재는 모두 즉시 정지. 차후 after_sell 로직 추가 가능.
    bot = await get_or_create_bot(user, db)
    bot.status = BotStatus.STOPPED
    await db.commit()
    tasks = getattr(request.app.state, "trading_tasks", {})
    if user.id in tasks:
        task = tasks.pop(user.id)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    return MessageResponse(message="봇이 정지되었습니다")


@router.get("/config")
async def get_config(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bot = await get_or_create_bot(user, db)
    config = bot.config or {}
    return {
        "max_investment_ratio": config.get("max_investment_ratio", 0.5),
        "max_positions": config.get("max_positions", 7),
        "stop_loss_pct": config.get("stop_loss_pct", 2.5),
        "take_profit_pct": config.get("take_profit_pct", 7.0),
        "telegram_chat_id": user.telegram_chat_id or "",
    }


@router.put("/config", response_model=MessageResponse)
async def update_config(
    req: BotConfigRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bot = await get_or_create_bot(user, db)
    config = dict(bot.config or {})
    if req.max_investment_ratio is not None:
        config["max_investment_ratio"] = req.max_investment_ratio
    if req.max_positions is not None:
        config["max_positions"] = req.max_positions
    if req.stop_loss_pct is not None:
        config["stop_loss_pct"] = req.stop_loss_pct
    if req.take_profit_pct is not None:
        config["take_profit_pct"] = req.take_profit_pct
    if req.telegram_chat_id is not None:
        user.telegram_chat_id = req.telegram_chat_id.strip() or None
    bot.config = config
    attributes.flag_modified(bot, "config")
    await db.commit()
    await db.refresh(bot)
    await db.refresh(user)
    return MessageResponse(message="설정이 저장되었습니다")


@router.get("/balance")
async def get_balance(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """업비트 원화·코인 잔고 조회. API 키 필요."""
    result = await db.execute(select(ApiKey).where(ApiKey.user_id == user.id, ApiKey.is_active == True))
    api_key = result.scalar_one_or_none()
    if not api_key:
        return {"krw": 0, "assets": [], "error": "API 키를 등록해 주세요"}
    try:
        access_key = decrypt_api_key(api_key.encrypted_api_key)
        secret_key = decrypt_api_key(api_key.encrypted_api_secret)
    except Exception:
        return {"krw": 0, "assets": [], "error": "API 키 복호화 실패"}
    try:
        client = UpbitClient(access_key, secret_key)
        accounts = await client.get_accounts()
        krw = 0.0
        assets = []
        for acc in accounts:
            currency = acc.get("currency", "")
            balance = float(acc.get("balance", 0) or 0)
            if currency == "KRW":
                krw = balance
            else:
                assets.append({
                    "currency": currency,
                    "balance": balance,
                    "avg_buy_price": float(acc.get("avg_buy_price", 0) or 0),
                })
        return {"krw": round(krw, 0), "assets": assets}
    except Exception as e:
        return {"krw": 0, "assets": [], "error": str(e)}


@router.get("/positions")
async def get_positions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Position).where(Position.user_id == user.id))
    positions = result.scalars().all()
    return [{"coin": p.coin, "quantity": p.total_quantity, "avg_price": p.avg_entry_price} for p in positions]


@router.get("/pnl-history")
async def get_pnl_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="일별 집계 일수"),
):
    """일별 실현 손익 시계열. KST 기준 일별로 realized_pnl 합산. 거래 없으면 0."""
    kst = timezone(timedelta(hours=9))
    since = datetime.now(kst) - timedelta(days=days)
    since_utc = since.replace(tzinfo=None) - timedelta(hours=9)
    result = await db.execute(
        select(Trade).where(Trade.user_id == user.id, Trade.created_at >= since_utc)
    )
    trades = result.scalars().all()
    by_date = defaultdict(lambda: {"pnl": 0.0, "pnl_krw": 0.0})
    for t in trades:
        day_kst = t.created_at + timedelta(hours=9)
        date_str = day_kst.strftime("%Y-%m-%d")
        pnl = t.realized_pnl or 0
        by_date[date_str]["pnl"] += pnl
        by_date[date_str]["pnl_krw"] += pnl
    out = []
    for i in range(days):
        d = (datetime.now(kst) - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        out.append({
            "date": d,
            "pnl": round(by_date[d]["pnl"], 2),
            "pnl_krw": round(by_date[d]["pnl_krw"], 0),
        })
    return out


@router.get("/trades")
async def get_trades(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="조회 기간(일). 7, 30, 90 등"),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(Trade)
        .where(Trade.user_id == user.id, Trade.created_at >= since)
        .order_by(Trade.created_at.desc())
        .limit(50)
    )
    trades = result.scalars().all()
    return [
        {
            "coin": t.coin,
            "side": t.side,
            "price": t.price,
            "quantity": t.quantity,
            "created_at": t.created_at.isoformat(),
        }
        for t in trades
    ]


@router.get("/trades/export")
async def export_trades_csv(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="내보내기 기간(일). 7, 30, 90 등"),
):
    """거래내역 CSV 내보내기. UTF-8 BOM. 헤더: 날짜,코인,구분,가격,수량,금액,실현손익"""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(Trade)
        .where(Trade.user_id == user.id, Trade.created_at >= since)
        .order_by(Trade.created_at.desc())
        .limit(500)
    )
    trades = result.scalars().all()
    buf = io.StringIO()
    buf.write("\ufeff")  # UTF-8 BOM for Excel
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["날짜", "코인", "구분", "가격", "수량", "금액", "실현손익"])
    for t in trades:
        side_kr = "매수" if (t.side or "").lower() in ("bid", "buy") else "매도"
        w.writerow([
            t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else "",
            t.coin or "",
            side_kr,
            t.price or 0,
            t.quantity or 0,
            t.total_amount or 0,
            t.realized_pnl if t.realized_pnl is not None else "",
        ])
    body = buf.getvalue().encode("utf-8")
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=trades_export.csv"},
    )


@router.post("/api-keys", response_model=MessageResponse, status_code=201)
async def add_api_key(
    req: ApiKeyCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 상용앱: 동일 사용자·동일 거래소(업비트) 활성 키 1개만 허용 — 중복 등록 방지
    existing = await db.execute(
        select(ApiKey).where(
            ApiKey.user_id == user.id,
            ApiKey.exchange == "upbit",
            ApiKey.is_active == True,
        )
    )
    if existing.scalars().first() is not None:
        raise HTTPException(
            status_code=400,
            detail="이미 업비트 API 키가 등록되어 있습니다. 기존 키를 삭제한 후 다시 등록해 주세요.",
        )
    api_key = ApiKey(
        user_id=user.id,
        exchange="upbit",
        label=req.label or "기본",
        encrypted_api_key=encrypt_api_key(req.access_key),
        encrypted_api_secret=encrypt_api_key(req.secret_key),
    )
    db.add(api_key)
    await db.commit()
    return MessageResponse(message="API 키가 등록되었습니다")


@router.get("/api-keys")
async def list_api_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ApiKey).where(ApiKey.user_id == user.id))
    keys = result.scalars().all()
    return [
        ApiKeyResponse(
            id=k.id,
            exchange=k.exchange,
            label=k.label,
            masked_key="••••••••",
            is_active=k.is_active,
        )
        for k in keys
    ]


@router.delete("/api-keys/{key_id}", response_model=MessageResponse)
async def delete_api_key(
    key_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API 키를 찾을 수 없음")
    db.delete(key)  # SQLAlchemy 2.0 AsyncSession: delete는 동기 메서드
    await db.commit()
    return MessageResponse(message="API 키가 삭제되었습니다")
