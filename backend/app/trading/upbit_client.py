"""
업비트 API 클라이언트
참조: https://docs.upbit.com/kr/reference/api-overview
- REST: 주문, 잔고, 캔들
- Rate Limit: 초당 10회
"""

import jwt
import uuid
import hashlib
import time
import asyncio
from urllib.parse import urlencode, unquote
from typing import Optional, Dict, List

import httpx

UPBIT_REST_URL = "https://api.upbit.com/v1"


class UpbitClient:
    """업비트 REST API 비동기 클라이언트"""

    def __init__(self, access_key: str, secret_key: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self._last_request = 0.0
        self._interval = 0.1
        self._lock = asyncio.Lock()

    def _create_token(self, query: Optional[Dict] = None) -> str:
        payload = {"access_key": self.access_key, "nonce": str(uuid.uuid4())}
        if query:
            qs = unquote(urlencode(query, doseq=True))
            payload["query_hash"] = hashlib.sha512(qs.encode()).hexdigest()
            payload["query_hash_alg"] = "SHA512"
        return f"Bearer {jwt.encode(payload, self.secret_key, algorithm='HS256')}"

    async def _request(self, method: str, url: str, **kwargs) -> Dict:
        async with self._lock:
            now = time.time()
            if now - self._last_request < self._interval:
                await asyncio.sleep(self._interval - (now - self._last_request))
            async with httpx.AsyncClient() as client:
                r = await client.request(method, url, **kwargs)
                self._last_request = time.time()
                r.raise_for_status()
                return r.json()

    async def get_accounts(self) -> List[Dict]:
        """계정 잔고 조회"""
        url = f"{UPBIT_REST_URL}/accounts"
        return await self._request("GET", url, headers={"Authorization": self._create_token()})

    async def get_krw_balance(self) -> float:
        """원화 잔고"""
        for acc in await self.get_accounts():
            if acc["currency"] == "KRW":
                return float(acc.get("balance", 0))
        return 0.0

    async def get_ticker(self, markets: List[str]) -> List[Dict]:
        """현재가 조회"""
        url = f"{UPBIT_REST_URL}/ticker"
        return await self._request("GET", url, params={"markets": ",".join(markets)})

    async def get_candles(self, market: str, interval: str = "minutes/15", count: int = 200) -> List[Dict]:
        """캔들 조회"""
        url = f"{UPBIT_REST_URL}/candles/{interval}"
        return await self._request("GET", url, params={"market": market, "count": count})

    async def place_order(
        self,
        market: str,
        side: str,
        volume: Optional[float] = None,
        price: Optional[float] = None,
        ord_type: str = "limit",
    ) -> Dict:
        """주문 생성 — ord_type: limit, price(시장가매수), market(시장가매도)"""
        query = {"market": market, "side": side, "ord_type": ord_type}
        if volume is not None:
            query["volume"] = str(volume)
        if price is not None:
            query["price"] = str(price)
        url = f"{UPBIT_REST_URL}/orders"
        return await self._request(
            "POST", url, headers={"Authorization": self._create_token(query)}, json=query
        )

    async def cancel_order(self, order_uuid: str) -> Dict:
        """주문 취소"""
        url = f"{UPBIT_REST_URL}/order"
        query = {"uuid": order_uuid}
        return await self._request(
            "DELETE", url, headers={"Authorization": self._create_token(query)}, params=query
        )
