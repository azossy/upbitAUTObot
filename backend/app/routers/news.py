"""
뉴스·공지 API — 실시간 코인 뉴스, 업비트 공지 목록 제공.
- 코인 뉴스: CryptoCompare News API (무료) 사용.
- 업비트 공지: 공지 페이지 링크 및 (가능 시) 목록 크롤링.
"""

from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.middleware.auth_middleware import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/news", tags=["뉴스·공지"])


class NewsItem(BaseModel):
    title: str
    url: str
    source: str
    published_at: str | None  # ISO 8601 또는 None
    body_snippet: str | None = None


class NewsListResponse(BaseModel):
    items: list[NewsItem]


# CryptoCompare News API (무료, API 키 없이 호출 가능)
CRYPTOCOMPARE_NEWS_URL = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
# 업비트 공지 목록 페이지 (앱에서 여기로 링크)
UPBIT_NOTICE_LIST_URL = "https://www.upbit.com/support/notice_list"


async def _fetch_coin_news(limit: int = 30) -> list[dict[str, Any]]:
    """CryptoCompare에서 코인 뉴스 목록 조회."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(CRYPTOCOMPARE_NEWS_URL)
            r.raise_for_status()
            data = r.json()
    except Exception:
        return []

    raw_list = data.get("Data") or []
    out = []
    for item in raw_list[:limit]:
        ts = item.get("published_on")
        published_at = (
            datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if isinstance(ts, (int, float)) else None
        )
        body = (item.get("body") or "")[:200].strip()
        if body and len((item.get("body") or "")) > 200:
            body = body + "..."
        src = item.get("source")
        if not src and isinstance(item.get("source_info"), dict):
            src = item["source_info"].get("name")
        out.append({
            "title": item.get("title") or "(제목 없음)",
            "url": item.get("url") or item.get("guid") or "",
            "source": src or "CryptoCompare",
            "published_at": published_at,
            "body_snippet": body or None,
        })
    return out


@router.get("/coin", response_model=NewsListResponse)
async def get_coin_news(
    limit: int = 30,
    user: User = Depends(get_current_user),
):
    """실시간 코인 뉴스 목록 (CryptoCompare 기반)."""
    items = await _fetch_coin_news(limit=limit)
    return NewsListResponse(
        items=[NewsItem(**x) for x in items],
    )


@router.get("/upbit", response_model=NewsListResponse)
async def get_upbit_notices(
    user: User = Depends(get_current_user),
):
    """업비트 공지사항. 목록이 없으면 공지 페이지 링크 1건 반환."""
    # 업비트는 공개 공지 API가 없어, 여기서는 공지 목록 페이지 링크를 제공.
    # 추후 업비트 공지 페이지 크롤링/API 연동 시 여기에 목록 추가 가능.
    return NewsListResponse(
        items=[
            NewsItem(
                title="업비트 공지사항 보기",
                url=UPBIT_NOTICE_LIST_URL,
                source="업비트",
                published_at=None,
                body_snippet="업비트 공지사항 전체 목록을 확인합니다.",
            ),
        ],
    )
