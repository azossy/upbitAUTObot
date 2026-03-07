#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
포트폴리오 배분 로직 검증 — 전략별 allocate_by_strategy 동작 확인.

의존성 없이 배분 수식만 검증합니다. (app.trading.engine와 동일한 로직을 인라인)
실행: python backend/tests/test_portfolio_allocation.py
"""

from __future__ import annotations


def allocate_krw_by_scores(
    total_krw: float,
    market_scores: list[tuple[str, float]],
    min_per_market: float = 5000.0,
) -> dict[str, float]:
    """점수 비율 그대로 배분."""
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
    """전략별 배분 (engine.py와 동일)."""
    if not market_scores or total_krw < min_per_market:
        return {}
    eligible = [(m, max(0.0, s)) for m, s in market_scores if m]
    if not eligible:
        return {}
    if strategy == "profit_first":
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
        n = len(eligible)
        krw_each = total_krw / n
        if krw_each < min_per_market:
            return {}
        return {m: round(krw_each, 0) for m, _ in eligible}
    return allocate_krw_by_scores(total_krw, market_scores, min_per_market)


def test_empty_markets():
    assert allocate_by_strategy(1_000_000, [], "balanced") == {}
    assert allocate_by_strategy(1_000_000, [], "profit_first") == {}


def test_insufficient_total():
    markets = [("KRW-BTC", 1.0), ("KRW-ETH", 1.0)]
    assert allocate_by_strategy(1000, markets, "balanced") == {}
    assert allocate_by_strategy(0, markets, "loss_min") == {}


def test_balanced_equal():
    markets = [("KRW-BTC", 1.0), ("KRW-ETH", 1.0), ("KRW-SOL", 1.0)]
    out = allocate_by_strategy(300_000, markets, "balanced")
    assert len(out) == 3
    assert out["KRW-BTC"] == 100_000 and out["KRW-ETH"] == 100_000 and out["KRW-SOL"] == 100_000
    out2 = allocate_by_strategy(300_000, markets, "loss_min")
    assert out2 == out


def test_engine_decision_proportional():
    markets = [("KRW-BTC", 5.0), ("KRW-ETH", 3.0), ("KRW-SOL", 2.0)]
    out = allocate_by_strategy(100_000, markets, "engine_decision")
    assert len(out) == 3 and sum(out.values()) == 100_000
    assert out["KRW-BTC"] == 50_000 and out["KRW-ETH"] == 30_000 and out["KRW-SOL"] == 20_000


def test_profit_first_tilts():
    markets = [("KRW-BTC", 3.0), ("KRW-ETH", 2.0), ("KRW-SOL", 1.0)]
    out = allocate_by_strategy(100_000, markets, "profit_first")
    assert len(out) == 3 and sum(out.values()) == 100_000
    assert out["KRW-BTC"] > out["KRW-ETH"] > out["KRW-SOL"]


def test_min_per_market():
    markets = [("KRW-BTC", 1.0), ("KRW-ETH", 1.0), ("KRW-SOL", 1.0)]
    out = allocate_by_strategy(10_000, markets, "balanced")
    assert out == {}  # 10000/3 < 5000


def test_allocate_krw_by_scores():
    markets = [("KRW-BTC", 2.0), ("KRW-ETH", 1.0)]
    out = allocate_krw_by_scores(150_000, markets)
    assert out["KRW-BTC"] == 100_000 and out["KRW-ETH"] == 50_000


if __name__ == "__main__":
    test_empty_markets()
    test_insufficient_total()
    test_balanced_equal()
    test_engine_decision_proportional()
    test_profit_first_tilts()
    test_min_per_market()
    test_allocate_krw_by_scores()
    print("All portfolio allocation tests passed.")
