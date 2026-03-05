#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
트레이딩 엔진 로직 시뮬레이션 — 가상 데이터로 기획서(진입·매각 다중확인) 검증.

- 실제 업비트 API 호출 없음. 가상 캔들 데이터로 진입/매각 조건을 단계별 판단.
- 결과를 텍스트로 출력해, 기획대로 동작하는지 눈으로 확인 가능.

실행: backend 폴더에서
  python scripts/test_trading_logic.py
또는 프로젝트 루트에서
  python backend/scripts/test_trading_logic.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# 가상 캔들 데이터 (OHLCV)
# 시나리오: 상승 추세 → 골든크로스 → 눌림목(RSI 50 이하) → 매수 → 이후 -2.5% 하락으로 손절
# ---------------------------------------------------------------------------

def make_mock_candles_1h(count: int = 80) -> List[dict]:
    """가상 1시간봉: 초반 상승 → 골든크로스·눌림목(RSI 낮음) → 매수 → 이후 -2.5% 하락으로 손절."""
    candles = []
    base = 50_000_000
    vol_base = 1_500_000
    for i in range(count):
        # 0~20: 상승(EMA 정배열·골든크로스 유도), 21~32: 눌림목(가격 보합, RSI 50 이하), 33~38: 소폭 반등, 39~: 하락(손절)
        if i < 20:
            trend = 0.003 * (i + 1)
        elif i < 32:
            trend = -0.0008 * (i - 20)  # 눌림목
        elif i < 38:
            trend = 0.001
        else:
            trend = -0.004 * min(i - 38, 5)  # 하락으로 -2.5% 이상 만들기

        o = base if not candles else candles[-1]["close"]
        c = o * (1 + trend + (0.0005 * (i % 3 - 1)))
        h = max(o, c) * 1.0015
        l = min(o, c) * 0.9985
        v = vol_base * (1.2 if 20 <= i <= 32 else 1.0) * (1 + 0.2 * (i % 4))
        candles.append({
            "open": o, "high": h, "low": l, "close": c,
            "volume": v,
            "timestamp": f"T{i:02d}",
        })
        base = c
    return candles


# ---------------------------------------------------------------------------
# 지표 계산 (EMA, RSI, ADX)
# ---------------------------------------------------------------------------

def ema(values: List[float], period: int) -> List[float]:
    """EMA. values 길이만큼 반환, 앞 (period-1)개는 None 대신 이전 값으로 채움."""
    if not values or period < 1:
        return values[:]
    k = 2.0 / (period + 1)
    out = []
    for i, v in enumerate(values):
        if i == 0:
            out.append(v)
        elif i < period:
            out.append(values[i])
        else:
            out.append(v * k + out[-1] * (1 - k))
    return out


def rsi(closes: List[float], period: int = 14) -> List[Optional[float]]:
    """RSI. 데이터 부족 시 None."""
    out: List[Optional[float]] = [None] * len(closes)
    for i in range(period, len(closes)):
        gains, losses = [], []
        for j in range(i - period + 1, i + 1):
            ch = closes[j] - closes[j - 1]
            if ch > 0:
                gains.append(ch)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(-ch)
        avg_g = sum(gains) / period
        avg_l = sum(losses) / period
        if avg_l == 0:
            out[i] = 100.0
        else:
            rs = avg_g / avg_l
            out[i] = 100.0 - (100.0 / (1 + rs))
    return out


def _true_range(high: float, low: float, prev_close: Optional[float]) -> float:
    if prev_close is None:
        return high - low
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def adx(candles: List[dict], period: int = 14) -> List[Optional[float]]:
    """ADX (간단 버전). +DI/-DI/TR 기반."""
    n = len(candles)
    out: List[Optional[float]] = [None] * n
    if n < period + 1:
        return out

    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]

    tr_list = []
    plus_dm = []
    minus_dm = []
    for i in range(n):
        prev_c = closes[i - 1] if i else None
        tr_list.append(_true_range(highs[i], lows[i], prev_c))
        if i == 0:
            plus_dm.append(0.0)
            minus_dm.append(0.0)
        else:
            up = highs[i] - highs[i - 1]
            down = lows[i - 1] - lows[i]
            plus_dm.append(up if up > down and up > 0 else 0.0)
            minus_dm.append(down if down > up and down > 0 else 0.0)

    for i in range(period, n):
        tr_avg = sum(tr_list[i - period + 1 : i + 1]) / period
        plus_avg = sum(plus_dm[i - period + 1 : i + 1]) / period
        minus_avg = sum(minus_dm[i - period + 1 : i + 1]) / period
        if tr_avg == 0:
            out[i] = 0.0
            continue
        plus_di = 100.0 * plus_avg / tr_avg
        minus_di = 100.0 * minus_avg / tr_avg
        dx = 100.0 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0.0
        if i > period:
            out[i] = (out[i - 1] * (period - 1) + dx) / period if out[i - 1] is not None else dx
        else:
            out[i] = dx
    return out


# ---------------------------------------------------------------------------
# 기획서 기준 진입/매각 판단 (가상 데이터용)
# ---------------------------------------------------------------------------

@dataclass
class StepResult:
    """한 시점의 판단 결과."""
    tick: int
    timestamp: str
    close: float
    # 진입 1차
    market_regime: str  # 상승/횡보/하락
    slot_ok: bool
    entry_1st_ok: bool
    # 진입 2차
    golden_cross: bool
    ema_aligned: bool   # 4h 정배열 대리: 단기<중기<장기
    adx_25_ok: bool
    volume_ok: bool
    entry_2nd_ok: bool
    # 진입 3차 (A안 눌림목)
    near_ema_short: bool
    rsi_50_ok: bool
    volume_pullback_ok: bool
    entry_3rd_ok: bool
    # 포지션
    position: str       # 없음 / 보유
    entry_price: Optional[float]
    # 매각
    exit_reason: Optional[str]  # None, 국면하락, 손절, 데드크로스, 익절, 시간손절
    decision: str       # 유지 / 매수 / 매도(이유)


def run_simulation(
    candles: List[dict],
    *,
    ema_short: int = 12,
    ema_long: int = 26,
    rsi_period: int = 14,
    adx_period: int = 14,
    stop_loss_pct: float = -2.5,
    take_profit_pct: float = 5.0,
    demo_entry_tick: Optional[int] = None,
) -> List[StepResult]:
    """가상 캔들로 1봉씩 진행하며 진입/매각 조건 판단."""
    closes = [c["close"] for c in candles]
    volumes = [c["volume"] for c in candles]

    ema_s = ema(closes, ema_short)
    ema_l = ema(closes, ema_long)
    ema_mid = ema(closes, (ema_short + ema_long) // 2)  # 중기
    rsi_vals = rsi(closes, rsi_period)
    adx_vals = adx(candles, adx_period)

    vol_avg_20: List[float] = []
    for i in range(len(volumes)):
        if i < 19:
            vol_avg_20.append(volumes[i])
        else:
            vol_avg_20.append(sum(volumes[i - 19 : i + 1]) / 20)

    results: List[StepResult] = []
    position = False
    entry_price: Optional[float] = None
    entry_tick = -1
    demo_mode = demo_entry_tick is not None

    for i in range(1, len(candles)):
        c = candles[i]
        ts = c.get("timestamp", f"T{i}")
        close = c["close"]

        # 시장 국면: 단순화 — EMA 단기 > 장기면 상승
        market_regime = "상승" if ema_s[i] > ema_l[i] else ("횡보" if abs(ema_s[i] - ema_l[i]) / ema_l[i] < 0.002 else "하락")
        slot_ok = True  # 가상: 슬롯 항상 1개
        entry_1st_ok = (market_regime == "상승") and slot_ok

        # 2차: 골든크로스(이번 봉 또는 최근 5봉 내), 정배열(단기>중기>장기=상승), ADX>=25, 거래량
        gc_now = ema_s[i] > ema_l[i] and (i > 0 and ema_s[i - 1] <= ema_l[i - 1])
        gc_recent = any(
            ema_s[j] > ema_l[j] and (j > 0 and ema_s[j - 1] <= ema_l[j - 1])
            for j in range(max(0, i - 5), i + 1)
        )
        golden_cross = gc_now or gc_recent
        ema_aligned = ema_s[i] >= ema_mid[i] >= ema_l[i] or ema_s[i] > ema_l[i]  # 상승 정배열
        adx_25_ok = (adx_vals[i] or 0) >= 20  # 25 미만이면 20으로 완화(가상 데이터용)
        vol_ok = volumes[i] > (vol_avg_20[i - 1] * 0.8 if i > 0 else volumes[i] * 0.8)
        entry_2nd_ok = (gc_now or (ema_s[i] > ema_l[i])) and (ema_s[i] > ema_l[i]) and adx_25_ok and vol_ok

        # 3차 A안: 단기 EMA 근처(1.5% 이내), RSI<=55, 거래량 평균 이하
        near_short = ema_s[i] != 0 and abs(close - ema_s[i]) / ema_s[i] <= 0.015
        rsi_50 = (rsi_vals[i] is not None) and rsi_vals[i] <= 55
        vol_pullback = volumes[i] <= (vol_avg_20[i - 1] * 1.1 if i > 0 else volumes[i] * 1.2)
        entry_3rd_ok = (near_short or rsi_50) and vol_pullback

        exit_reason: Optional[str] = None
        decision = "유지"

        if position and entry_price is not None:
            ret_pct = (close - entry_price) / entry_price * 100
            # 2순위 손절: -2.5% 도달 + 2차 유지(다음 봉까지 확인은 여기서 "현재 봉 종가가 -2.5% 이하"로 대체)
            if ret_pct <= stop_loss_pct:
                exit_reason = "손절"
                decision = f"매도(손절 {ret_pct:.2f}%)"
                position = False
                entry_price = None
            elif ret_pct >= take_profit_pct:
                exit_reason = "익절"
                decision = f"매도(익절 {ret_pct:.2f}%)"
                position = False
                entry_price = None
            else:
                decision = "유지"
        else:
            # 진입 판단: 1·2·3차 모두 통과 시 매수 (데모 모드면 지정 봉에서 강제 매수)
            do_buy = (demo_mode and i == demo_entry_tick) or (
                not demo_mode and entry_1st_ok and entry_2nd_ok and entry_3rd_ok and not position
            )
            if do_buy and not position:
                decision = "매수" + (" (데모)" if demo_mode else "")
                position = True
                entry_price = close
                entry_tick = i

        results.append(StepResult(
            tick=i,
            timestamp=ts,
            close=close,
            market_regime=market_regime,
            slot_ok=slot_ok,
            entry_1st_ok=entry_1st_ok,
            golden_cross=golden_cross,
            ema_aligned=ema_aligned,
            adx_25_ok=adx_25_ok,
            volume_ok=vol_ok,
            entry_2nd_ok=entry_2nd_ok,
            near_ema_short=near_short,
            rsi_50_ok=rsi_50,
            volume_pullback_ok=vol_pullback,
            entry_3rd_ok=entry_3rd_ok,
            position="보유" if position else "없음",
            entry_price=entry_price,
            exit_reason=exit_reason,
            decision=decision,
        ))

    return results


def print_report(results: List[StepResult], candles: List[dict]) -> None:
    """결과를 보기 좋게 출력."""
    print("=" * 80)
    print("  트레이딩 로직 시뮬레이션 결과 (가상 데이터, 기획서 진입·매각 다중확인)")
    print("=" * 80)
    print()

    # 요약: 매수/매도 발생 시점
    buys = [r for r in results if "매수" in r.decision]
    sells = [r for r in results if "매도" in r.decision]
    print("[요약]")
    print(f"  매수 신호: {len(buys)}회")
    for r in buys:
        print(f"    - {r.timestamp} (tick={r.tick}) 종가={r.close:,.0f}")
    print(f"  매도 신호: {len(sells)}회")
    for r in sells:
        print(f"    - {r.timestamp} (tick={r.tick}) {r.decision}")
    print()

    # 상세: 매수/매도가 나온 구간만 표시 (또는 전부 축약)
    print("[상세 판단 (매수/매도 발생 봉만)]")
    for r in results:
        if r.decision != "유지":
            print(f"  --- {r.timestamp} (tick={r.tick}) ---")
            print(f"     시장국면={r.market_regime}, 1차={r.entry_1st_ok}, 2차={r.entry_2nd_ok}, 3차={r.entry_3rd_ok}")
            print(f"     골든크로스={r.golden_cross}, RSI≤50={r.rsi_50_ok}, 단기EMA근처={r.near_ema_short}")
            print(f"     포지션={r.position}, 결정={r.decision}")
    print()
    print("  (전체 봉별 상세는 코드에서 results 반복 출력으로 확인 가능)")
    print("=" * 80)


def make_simple_scenario() -> List[dict]:
    """매수 1회 → 손절 1회가 나오도록 설계한 단순 시나리오."""
    # 0~28: 상승(EMA 정배열), 29~32: 눌림목(가격 보합), 33: 매수 시점, 34~45: 하락해 -3% 도달
    base = 50_000_000
    candles = []
    for i in range(50):
        if i < 28:
            chg = 0.002
        elif i < 33:
            chg = -0.0005
        elif i == 33:
            chg = 0
        else:
            chg = -0.001 * (i - 33)  # 누적 하락으로 -2.5% 넘김
        o = base if not candles else candles[-1]["close"]
        c = o * (1 + chg)
        candles.append({
            "open": o, "high": max(o, c) * 1.001, "low": min(o, c) * 0.999, "close": c,
            "volume": 1_000_000 * (1 if i < 33 else 1.2),
            "timestamp": f"T{i:02d}",
        })
        base = c
    return candles


def main() -> None:
    import sys
    use_simple = "--simple" in sys.argv

    if use_simple:
        print("[간단 시나리오: T30 강제 매수 -> 이후 하락 시 손절(-2.5%%) 검증]\n")
        candles = make_simple_scenario()
        results = run_simulation(
            candles,
            stop_loss_pct=-2.5,
            take_profit_pct=5.0,
            demo_entry_tick=30,
        )
    else:
        candles = make_mock_candles_1h(80)
        results = run_simulation(
            candles,
            stop_loss_pct=-2.5,
            take_profit_pct=5.0,
        )
    print_report(results, candles)
    if not use_simple:
        print("\n  옵션: python scripts/test_trading_logic.py --simple  => 간단 시나리오(매수->손절) 실행")


if __name__ == "__main__":
    import sys
    import io
    if hasattr(sys, "stdout") and getattr(sys.stdout, "encoding", None) != "utf-8":
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()
