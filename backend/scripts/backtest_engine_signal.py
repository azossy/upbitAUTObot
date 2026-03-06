#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AntEngine 백테스트 — 과거 캔들을 시간순으로 재생하며 동일 /signal 스키마로 엔진 호출.

- Look-ahead 금지: 각 시점에서 그 시점까지의 캔들만 전달.
- 엔진이 실행 중이어야 함 (기본 http://127.0.0.1:9100).

사용법:
  # 엔진 기동 후 (ant_engine 또는 AntEngine-0.9.bin)
  python backend/scripts/backtest_engine_signal.py
  python backend/scripts/backtest_engine_signal.py --engine-url http://127.0.0.1:9100 --data backtest_data.json
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

try:
    import requests
except ImportError:
    requests = None


def make_sample_candles_1h(count: int = 80) -> list[dict[str, Any]]:
    """엔진 입력 형식: { t, o, h, l, c, v }."""
    out = []
    base = 50_000_000.0
    vol = 1_500_000.0
    for i in range(count):
        o = base if not out else out[-1]["c"]
        trend = 0.002 * min(i, 30) - 0.001 * max(0, i - 40)
        c = o * (1 + trend)
        h = max(o, c) * 1.002
        l = min(o, c) * 0.998
        out.append({
            "t": f"2026-03-01T{i:02d}:00:00Z",
            "o": o, "h": h, "l": l, "c": c, "v": vol * (1 + (i % 5) * 0.1)
        })
        base = c
    return out


def make_sample_candles_4h_from_1h(candles_1h: list[dict]) -> list[dict]:
    """1시간봉 4개마다 4시간봉 1개 (단순 집계)."""
    out = []
    for i in range(0, len(candles_1h), 4):
        chunk = candles_1h[i:i+4]
        if not chunk:
            break
        o = chunk[0]["o"]
        c = chunk[-1]["c"]
        h = max(k["h"] for k in chunk)
        l = min(k["l"] for k in chunk)
        v = sum(k["v"] for k in chunk)
        out.append({"t": chunk[-1]["t"], "o": o, "h": h, "l": l, "c": c, "v": v})
    return out


def build_request(
    candles_1h_slice: list[dict],
    candles_4h_slice: list[dict],
    current_price: float,
    timestamp_utc: str,
    request_id: str,
    market: str = "KRW-BTC",
    positions: list[dict] | None = None,
    market_regime: str = "up",
    market_score: float = 0.0,
) -> dict:
    """입출력 가이드 §2 형식의 시그널 요청 body."""
    return {
        "request_id": request_id,
        "timestamp_utc": timestamp_utc,
        "market": market,
        "mode": "both",
        "candles_1h": candles_1h_slice,
        "candles_4h": candles_4h_slice,
        "current_price": current_price,
        "positions": positions or [],
        "balance_krw": 10_000_000,
        "config": {
            "max_positions": 7,
            "stop_loss_pct": 2.5,
            "take_profit_pct": 7.0,
            "take_profit_tier1_pct": 5.0,
            "take_profit_tier2_pct": 10.0,
            "take_profit_tier3_pct": 15.0,
            "time_stop_hours": 12,
            "max_investment_ratio": 0.5,
            "event_window_active": False,
        },
        "market_regime": market_regime,
        "market_score": market_score,
    }


def run_backtest(
    engine_url: str,
    candles_1h: list[dict],
    candles_4h: list[dict],
    min_candles_1h: int = 26,
) -> list[dict]:
    """시간순 재생. 각 시점에서 그 시점까지의 데이터만 전달."""
    results = []
    for i in range(min_candles_1h, len(candles_1h)):
        slice_1h = candles_1h[: i + 1]
        t = candles_1h[i]["t"]
        ts_4h = t
        slice_4h = [x for x in candles_4h if x["t"] <= ts_4h] if candles_4h else []
        if not slice_4h and candles_4h:
            slice_4h = candles_4h[: (i // 4) + 1]

        req = build_request(
            slice_1h,
            slice_4h,
            current_price=candles_1h[i]["c"],
            timestamp_utc=t,
            request_id=f"bt-{i}",
        )
        try:
            r = requests.post(f"{engine_url.rstrip('/')}/signal", json=req, timeout=5)
            body = r.json()
        except Exception as e:
            body = {"status": "error", "error_message": str(e)}
        body["_step"] = i
        body["_t"] = t
        results.append(body)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="AntEngine 백테스트 (과거 캔들 재생)")
    parser.add_argument("--engine-url", default="http://127.0.0.1:9100", help="엔진 base URL")
    parser.add_argument("--data", help="JSON 파일 경로 (candles_1h, candles_4h 키). 없으면 샘플 데이터 사용")
    parser.add_argument("--min-candles", type=int, default=26, help="최소 1h 캔들 개수")
    args = parser.parse_args()

    if requests is None:
        print("pip install requests 필요", file=sys.stderr)
        return 1

    if args.data:
        with open(args.data, "r", encoding="utf-8") as f:
            data = json.load(f)
        candles_1h = data.get("candles_1h", [])
        candles_4h = data.get("candles_4h", [])
        if not candles_1h:
            print("candles_1h 없음", file=sys.stderr)
            return 1
    else:
        candles_1h = make_sample_candles_1h(80)
        candles_4h = make_sample_candles_4h_from_1h(candles_1h)

    print(f"1h 봉 수: {len(candles_1h)}, 4h 봉 수: {len(candles_4h)}")
    print(f"엔진: {args.engine_url}, min_candles: {args.min_candles}")
    print("재생 중 (look-ahead 없음)...")

    results = run_backtest(args.engine_url, candles_1h, candles_4h, args.min_candles)

    signals = {}
    for r in results:
        sig = r.get("signal", "error")
        signals[sig] = signals.get(sig, 0) + 1
        if r.get("signal") in ("buy", "sell"):
            print(f"  step {r.get('_step')} {r.get('_t')} -> {r.get('signal')} {r.get('reason_code', '')}")

    print("\n요약:")
    for k, v in sorted(signals.items()):
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
