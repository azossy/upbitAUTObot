#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
업비트 원화마켓 1h/4h 캔들 수집 — AntEngine 백테스트용.
pyupbit으로 KRW-BTC 등 지정 마켓의 과거 봉을 조회해 엔진 입력 형식 JSON으로 저장.

사용법 (backend 폴더 또는 프로젝트 루트에서):
  python backend/scripts/fetch_ohlcv_upbit.py --market KRW-BTC --from 2025-01-01 --to 2025-03-05
  python backend/scripts/fetch_ohlcv_upbit.py --market KRW-BTC --output backtest_data.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

try:
    import pyupbit
except ImportError:
    pyupbit = None

# 1h: 3600초, 4h: 14400초. 공백 판단 시 허용 오차(초).
TOL_SEC_1H = 120
TOL_SEC_4H = 300


def df_row_to_candle(row, t_iso: str) -> dict:
    return {
        "t": t_iso,
        "o": float(row["open"]),
        "h": float(row["high"]),
        "l": float(row["low"]),
        "c": float(row["close"]),
        "v": float(row["volume"]),
    }


def fetch_ohlcv_upbit(market: str, interval: str, from_ts: datetime, to_ts: datetime) -> list[dict]:
    """interval: minute60 또는 minute240. 반환: 시간 오름차순 [{t,o,h,l,c,v}, ...]."""
    if pyupbit is None:
        raise RuntimeError("pyupbit 미설치. pip install pyupbit")
    all_rows = []
    current_to = to_ts
    count = 200
    while current_to > from_ts:
        to_str = current_to.strftime("%Y-%m-%dT%H:%M:%S")
        df = pyupbit.get_ohlcv(market, interval=interval, count=count, to=to_str)
        if df is None or df.empty:
            break
        for idx in df.index:
            ts = idx.to_pydatetime()
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts < from_ts:
                continue
            t_iso = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
            row = df.loc[idx]
            all_rows.append((ts, df_row_to_candle(row, t_iso)))
        oldest = df.index.min().to_pydatetime()
        if oldest.tzinfo is None:
            oldest = oldest.replace(tzinfo=timezone.utc)
        current_to = oldest - timedelta(seconds=1)
        if len(df) < count:
            break
    all_rows.sort(key=lambda x: x[0])
    seen = set()
    unique = []
    for ts, c in all_rows:
        if c["t"] not in seen:
            seen.add(c["t"])
            unique.append(c)
    return unique


def find_gaps(candles: list[dict], expected_sec: int, tol_sec: int) -> list[tuple[datetime, datetime]]:
    """캔들 리스트에서 공백 구간 (from_ts, to_ts) 목록 반환. UTC datetime."""
    gaps = []
    for i in range(1, len(candles)):
        t0 = candles[i - 1]["t"]
        t1 = candles[i]["t"]
        try:
            dt0 = datetime.fromisoformat(t0.replace("Z", "+00:00"))
            dt1 = datetime.fromisoformat(t1.replace("Z", "+00:00"))
        except Exception:
            continue
        delta = (dt1 - dt0).total_seconds()
        if delta > expected_sec + tol_sec:
            gaps.append((dt0, dt1))
    return gaps


def fill_gaps_1h(market: str, candles: list[dict]) -> list[dict]:
    """1h 봉 공백 구간을 재요청으로 채움. 빠진 것 없이 기초 데이터셋 보강."""
    gaps = find_gaps(candles, 3600, TOL_SEC_1H)
    if not gaps:
        return candles
    filled = list(candles)
    for start_ts, end_ts in gaps:
        extra = fetch_ohlcv_upbit(market, "minute60", start_ts + timedelta(seconds=3600), end_ts)
        for c in extra:
            if not any(x["t"] == c["t"] for x in filled):
                filled.append(c)
        filled.sort(key=lambda x: x["t"])
    return filled


def fill_gaps_4h(market: str, candles: list[dict]) -> list[dict]:
    """4h 봉 공백 구간을 재요청으로 채움."""
    gaps = find_gaps(candles, 14400, TOL_SEC_4H)
    if not gaps:
        return candles
    filled = list(candles)
    for start_ts, end_ts in gaps:
        extra = fetch_ohlcv_upbit(market, "minute240", start_ts + timedelta(seconds=14400), end_ts)
        for c in extra:
            if not any(x["t"] == c["t"] for x in filled):
                filled.append(c)
        filled.sort(key=lambda x: x["t"])
    return filled


def main() -> int:
    parser = argparse.ArgumentParser(description="업비트 원화마켓 1h/4h 캔들 수집")
    parser.add_argument("--market", default="KRW-BTC", help="마켓 (예: KRW-BTC)")
    parser.add_argument("--from", dest="from_", default="2025-01-01", help="시작일 (YYYY-MM-DD)")
    parser.add_argument("--to", default=None, help="종료일 (YYYY-MM-DD). 미지정 시 오늘")
    parser.add_argument("--output", default="backtest_data.json", help="출력 JSON 경로")
    args = parser.parse_args()

    if pyupbit is None:
        print("pip install pyupbit 필요", file=sys.stderr)
        return 1

    from_ts = datetime.strptime(args.from_, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    to_ts = datetime.strptime(args.to, "%Y-%m-%d").replace(tzinfo=timezone.utc) if args.to else datetime.now(timezone.utc)

    print(f"수집: {args.market}, {from_ts.date()} ~ {to_ts.date()}")
    print("1시간봉 수집 중...")
    candles_1h = fetch_ohlcv_upbit(args.market, "minute60", from_ts, to_ts)
    print(f"  1h: {len(candles_1h)}개")
    g1 = find_gaps(candles_1h, 3600, TOL_SEC_1H)
    if g1:
        print(f"  1h 봉 공백 {len(g1)}곳 발견 → 재수집으로 보강 중...")
        candles_1h = fill_gaps_1h(args.market, candles_1h)
        print(f"  1h: {len(candles_1h)}개 (보강 후)")
    if len(candles_1h) < 26:
        print("1h 봉이 26개 미만입니다. 기간을 넓히거나 나중에 다시 시도하세요.", file=sys.stderr)
        return 1

    print("4시간봉 수집 중...")
    candles_4h = fetch_ohlcv_upbit(args.market, "minute240", from_ts, to_ts)
    print(f"  4h: {len(candles_4h)}개")
    g4 = find_gaps(candles_4h, 14400, TOL_SEC_4H)
    if g4:
        print(f"  4h 봉 공백 {len(g4)}곳 발견 → 재수집으로 보강 중...")
        candles_4h = fill_gaps_4h(args.market, candles_4h)
        print(f"  4h: {len(candles_4h)}개 (보강 후)")

    out = {
        "market": args.market,
        "from": args.from_,
        "to": args.to or to_ts.strftime("%Y-%m-%d"),
        "candles_1h": candles_1h,
        "candles_4h": candles_4h,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0)

    print(f"저장: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
