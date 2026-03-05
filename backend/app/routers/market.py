"""시세 API — 업비트 공개 ticker 프록시. app.state.http_client 재사용."""
from fastapi import APIRouter, Query, Request

UPBIT_TICKER_URL = "https://api.upbit.com/v1/ticker"
MAX_MARKETS = 20

router = APIRouter(prefix="/api/v1/market", tags=["시세"])


@router.get("/ticker")
async def get_ticker(
    request: Request,
    markets: str = Query(..., description="쉼표 구분 마켓 코드. 예: KRW-BTC,KRW-ETH. 최대 20개"),
):
    """업비트 공개 ticker API 프록시. 인증 불필요."""
    parts = [p.strip() for p in markets.split(",") if p.strip()][:MAX_MARKETS]
    if not parts:
        return []
    query = "&".join(f"markets={m}" for m in parts)
    client = getattr(request.app.state, "http_client", None)
    if client is None:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as fallback:
            r = await fallback.get(f"{UPBIT_TICKER_URL}?{query}")
            r.raise_for_status()
            return r.json()
    r = await client.get(f"{UPBIT_TICKER_URL}?{query}")
    r.raise_for_status()
    return r.json()
