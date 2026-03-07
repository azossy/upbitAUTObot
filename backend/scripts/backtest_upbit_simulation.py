#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
업비트 원화거래소 실데이터 + 개미엔진 모의 백테스트.
- 시드 100만 원(100% 자동매매), 실제 업비트 1h/4h 캔들로 엔진 호출.
- 단일 종목 실행 시 가용 금액 전부를 해당 종목에 투자. 다종목 선택 시에는 백엔드 allocate_krw_by_scores로 상승 가능성 비율 분산 매수.
- 진입/매각/익절/손절을 시뮬레이션하고, 일별 수익률·종목·엔진 판단(reason_code) 결과 보고.
- 엔진이 없으면 실행하지 않고, 사용자에게 알린 뒤 조치 지시를 기다림. (--no-engine 없음)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


def _parse_utc_ts(ts: str) -> datetime | None:
    """ISO8601 UTC 문자열을 datetime으로. 실패 시 None."""
    if not ts:
        return None
    try:
        s = (ts.replace("Z", "+00:00") if "Z" in ts else ts)
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _interval_label(sec: float) -> str:
    """초 단위 간격을 '1h', '60분' 형태로."""
    if sec <= 0:
        return "-"
    if sec >= 3600:
        return f"{sec / 3600:.1f}h"
    return f"{int(sec / 60)}분"


def validate_candle_data(candles_1h: list[dict], candles_4h: list[dict]) -> dict:
    """
    업비트 캔들 데이터 결측/공백 검사.
    반환: {"ok": bool, "1h_count", "4h_count", "1h_gaps": [...], "4h_gaps": [...], "message": str}
    """
    result = {"ok": True, "1h_count": len(candles_1h), "4h_count": len(candles_4h), "1h_gaps": [], "4h_gaps": [], "message": ""}
    expect_1h_sec = 3600
    expect_4h_sec = 14400
    tol_sec = 120  # 2분 오차 허용

    def check_gaps(candles: list[dict], expected_sec: int, label: str) -> list[dict]:
        gaps = []
        for i in range(1, len(candles)):
            prev_ts = _parse_utc_ts((candles[i - 1].get("t") or ""))
            curr_ts = _parse_utc_ts((candles[i].get("t") or ""))
            if prev_ts and curr_ts:
                delta = (curr_ts - prev_ts).total_seconds()
                if abs(delta - expected_sec) > tol_sec:
                    gaps.append({"index": i, "from": candles[i - 1].get("t"), "to": candles[i].get("t"), "delta_sec": int(delta)})
        return gaps

    result["1h_gaps"] = check_gaps(candles_1h, expect_1h_sec, "1h")
    result["4h_gaps"] = check_gaps(candles_4h, expect_4h_sec, "4h")
    if result["1h_gaps"] or result["4h_gaps"]:
        result["ok"] = False
        msgs = []
        if result["1h_gaps"]:
            msgs.append(f"1h 봉 공백 {len(result['1h_gaps'])}곳 (예: 인덱스 {result['1h_gaps'][0]['index']} 구간)")
        if result["4h_gaps"]:
            msgs.append(f"4h 봉 공백 {len(result['4h_gaps'])}곳 (예: 인덱스 {result['4h_gaps'][0]['index']} 구간)")
        result["message"] = "; ".join(msgs)
    else:
        result["message"] = "1h·4h 봉 연속성 확인됨(결측 없음)."
    return result

try:
    import requests
except ImportError:
    requests = None

ENGINE_HEALTH_TIMEOUT = 3
ENGINE_START_WAIT_SEC = 2

# 동일 디렉터리 backtest_engine_signal 모듈 사용
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
from backtest_engine_signal import build_request, make_sample_candles_1h, make_sample_candles_4h_from_1h

INITIAL_KRW = 1_000_000  # 시드 100만 원
MAX_INVESTMENT_RATIO = 1.0  # 100% 자동매매 적용

# 진입 완화 프로필 (docs/시뮬레이션_진입_보수성_분석_및_완화방안.md 적용순서 1~4)
# 프로필 1: 방안1만(ADX 25→22), 2: +방안2(EMA 2%, RSI 55), 3: +방안4(B안 완화), 4: +방안6(3차 C안)
def get_entry_profile_config(profile: int) -> dict:
    """엔진 config에 넣을 진입 완화 오버라이드. 0이면 엔진 기본값 사용."""
    base = {
        "adx_entry_threshold": 0,
        "ema_tolerance_pct": 0,
        "rsi_pullback_max": 0,
        "market_score_strong": 0,
        "adx_strong_1h": 0,
        "adx_strong_4h": 0,
        "allow_entry_3c": False,
    }
    if profile <= 0:
        return base
    # 1: ADX 22
    if profile >= 1:
        base["adx_entry_threshold"] = 22.0
    if profile >= 2:
        base["ema_tolerance_pct"] = 0.02
        base["rsi_pullback_max"] = 55.0
    if profile >= 3:
        base["market_score_strong"] = 6.0
        base["adx_strong_1h"] = 30.0
        base["adx_strong_4h"] = 25.0
    if profile >= 4:
        base["allow_entry_3c"] = True
    return base

# 시장 점수: 최근 20봉 수익률(%) 기반 0~10. 엔진 Stage3B(market_score>=8) 진입용.
def compute_market_score(candles_1h_slice: list[dict], current_price: float, lookback: int = 20) -> float:
    if not candles_1h_slice or len(candles_1h_slice) < lookback:
        return 0.0
    past_close = candles_1h_slice[-lookback].get("c") or candles_1h_slice[-lookback].get("close")
    if not past_close or past_close <= 0:
        return 0.0
    ret_pct = (current_price - past_close) / past_close * 100.0
    return max(0.0, min(10.0, ret_pct * 2.0))  # 5% 상승 -> 10점


def check_engine_health(engine_url: str) -> bool:
    """엔진 /health 또는 /version 응답 확인. 연결 가능하면 True."""
    if not requests:
        return False
    base = engine_url.rstrip("/")
    for path in ("/health", "/version"):
        try:
            r = requests.get(f"{base}{path}", timeout=ENGINE_HEALTH_TIMEOUT)
            if r.status_code == 200:
                return True
        except Exception:
            continue
    return False


def find_engine_binary() -> str | None:
    """프로젝트 루트 기준 ant_engine 빌드 경로 탐색."""
    # backend/scripts/ -> backend/ -> 프로젝트 루트
    backend_dir = os.path.dirname(SCRIPT_DIR)
    root = os.path.dirname(backend_dir)
    candidates = [
        os.path.join(root, "ant_engine", "build", "ant_engine.exe"),
        os.path.join(root, "ant_engine", "build", "AntEngine-1.0.bin"),
        os.path.join(root, "ant_engine", "release", "AntEngine-1.0.bin"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def ensure_engine_running(engine_url: str) -> bool:
    """
    엔진 연결 확인. 실패 시 바이너리 자동 기동 시도 후 재확인.
    성공 시 True, 실패 시 False (호출 측에서 메시지 출력 후 종료).
    """
    if check_engine_health(engine_url):
        return True
    binary = find_engine_binary()
    if not binary:
        return False
    try:
        subprocess.Popen(
            [binary],
            cwd=os.path.dirname(binary),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        )
    except Exception:
        return False
    time.sleep(ENGINE_START_WAIT_SEC)
    return check_engine_health(engine_url)


def position_to_engine(pos: dict) -> dict:
    return {
        "market": pos["market"],
        "quantity": pos["quantity"],
        "avg_entry_price": pos["avg_entry_price"],
        "entry_timestamp_utc": pos["entry_timestamp_utc"],
        "sold_tier1": pos.get("sold_tier1", False),
        "sold_tier2": pos.get("sold_tier2", False),
        "sold_tier3": pos.get("sold_tier3", False),
    }


def run_simulation(
    engine_url: str,
    candles_1h: list[dict],
    candles_4h: list[dict],
    market: str = "KRW-BTC",
    min_candles_1h: int = 26,
    max_steps: int | None = None,
    entry_profile: int = 0,
) -> tuple[list[dict], list[dict], list[dict]]:
    """
    시뮬레이션: balance_krw=100만, max_investment_ratio=1.0.
    entry_profile: 0=엔진 기본값, 1~4=진입 완화 적용순서(1:ADX22, 2:+3차A완화, 3:+3차B완화, 4:+3차C안).
    반환: (엔진 응답 목록, 거래 로그, 일별 PnL 요약).
    """
    balance_krw = float(INITIAL_KRW)
    positions: list[dict] = []  # { market, quantity, avg_entry_price, entry_timestamp_utc, sold_tier1/2/3 }
    trades: list[dict] = []
    engine_responses: list[dict] = []

    end_i = len(candles_1h)
    if max_steps is not None:
        end_i = min(end_i, min_candles_1h + max_steps)
    for i in range(min_candles_1h, end_i):
        slice_1h = candles_1h[: i + 1]
        t = candles_1h[i]["t"]
        ts_4h = t
        slice_4h = [x for x in candles_4h if x["t"] <= ts_4h] if candles_4h else []
        if not slice_4h and candles_4h:
            slice_4h = candles_4h[: (i // 4) + 1]

        current_price = candles_1h[i]["c"]
        positions_engine = [position_to_engine(p) for p in positions]
        config = {
            "max_positions": 7,
            "stop_loss_pct": 2.5,
            "take_profit_pct": 7.0,
            "take_profit_tier1_pct": 5.0,
            "take_profit_tier2_pct": 10.0,
            "take_profit_tier3_pct": 15.0,
            "time_stop_hours": 12,
            "max_investment_ratio": MAX_INVESTMENT_RATIO,
            "event_window_active": False,
        }
        config.update(get_entry_profile_config(entry_profile))
        market_score = compute_market_score(slice_1h, current_price)
        req = build_request(
            slice_1h,
            slice_4h,
            current_price=current_price,
            timestamp_utc=t,
            request_id=f"sim-{i}",
            market=market,
            positions=positions_engine,
            market_regime="up",
            market_score=market_score,
        )
        req["balance_krw"] = balance_krw
        req["config"] = config

        try:
            r = requests.post(f"{engine_url.rstrip('/')}/signal", json=req, timeout=5)
            body = r.json()
        except Exception as e:
            body = {"status": "error", "error_message": str(e), "signal": "hold"}
        now_utc = datetime.now(timezone.utc)
        now_local = datetime.now()  # 시스템 로컬 시각
        body["_step"] = i
        body["_t"] = t
        body["_price"] = current_price
        body["_response_time_utc"] = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        body["_response_time_local"] = now_local.strftime("%Y-%m-%d %H:%M:%S")  # 우리 시스템 기준 시/분/초
        body["_positions_count"] = len(positions)
        body["_balance_krw"] = balance_krw
        engine_responses.append(body)

        if body.get("status") != "ok":
            continue
        signal = body.get("signal", "hold")
        reason_code = body.get("reason_code", "")

        if signal == "buy" and balance_krw > 0:
            # 단일 종목 가정: 가용 금액 전부 또는 1포지션당 투자
            invest_krw = balance_krw * MAX_INVESTMENT_RATIO
            if invest_krw < 5000:  # 최소 주문 금액
                continue
            qty = invest_krw / current_price
            if qty <= 0:
                continue
            cost = qty * current_price
            balance_krw -= cost
            positions.append({
                "market": market,
                "quantity": qty,
                "avg_entry_price": current_price,
                "entry_timestamp_utc": t,
                "sold_tier1": False,
                "sold_tier2": False,
                "sold_tier3": False,
            })
            trades.append({
                "timestamp_utc": t,
                "market": market,
                "side": "buy",
                "price": current_price,
                "quantity": qty,
                "amount_krw": cost,
                "reason_code": reason_code,
                "balance_after": balance_krw,
            })

        elif signal == "sell" and positions:
            sell_qty = body.get("quantity")
            if sell_qty is None or sell_qty <= 0:
                sell_qty = positions[0]["quantity"]
            pos = positions[0]
            actual_sell = min(sell_qty, pos["quantity"])
            if actual_sell <= 0:
                continue
            revenue = actual_sell * current_price
            pnl = revenue - actual_sell * pos["avg_entry_price"]
            balance_krw += revenue
            trades.append({
                "timestamp_utc": t,
                "market": market,
                "side": "sell",
                "price": current_price,
                "quantity": actual_sell,
                "amount_krw": revenue,
                "reason_code": reason_code,
                "pnl_krw": pnl,
                "balance_after": balance_krw,
            })
            if actual_sell >= pos["quantity"]:
                positions.pop(0)
            else:
                pos["quantity"] -= actual_sell
                if "tier1" in reason_code:
                    pos["sold_tier1"] = True
                elif "tier2" in reason_code:
                    pos["sold_tier2"] = True
                elif "tier3" in reason_code:
                    pos["sold_tier3"] = True

    # 일별 PnL: 거래 로그에서 날짜별 실현 손익 + 당일 종료 시점 미청산 평가손익(선택)
    daily: dict[str, dict] = defaultdict(lambda: {"pnl_krw": 0.0, "trades": 0})
    for tr in trades:
        if tr["side"] != "sell":
            continue
        date_key = tr["timestamp_utc"][:10]
        daily[date_key]["pnl_krw"] += tr.get("pnl_krw", 0)
        daily[date_key]["trades"] += 1

    daily_list = []
    cum = 0.0
    for d in sorted(daily.keys()):
        cum += daily[d]["pnl_krw"]
        daily_list.append({
            "date": d,
            "daily_pnl_krw": round(daily[d]["pnl_krw"], 2),
            "daily_pnl_pct": round(100 * daily[d]["pnl_krw"] / INITIAL_KRW, 4),
            "cumulative_pnl_krw": round(cum, 2),
            "cumulative_pnl_pct": round(100 * cum / INITIAL_KRW, 4),
            "trades_count": daily[d]["trades"],
        })

    return engine_responses, trades, daily_list


# 개미엔진 진입은 3단계: 1차(국면·슬롯) → 2차(1h·4h 정배열, ADX) → 3차 A안/3차 B안
def stage_from_reason(reason_code: str) -> tuple[str, str, str, str, str]:
    """reason_code → (1차, 2차, 3차, 3-1스테이지(A안), 3-2스테이지(B안))."""
    if not reason_code:
        return "-", "-", "-", "-", "-"
    if reason_code == "hold_stage1":
        return "미통과", "-", "-", "-", "-"
    if reason_code == "hold_stage2":
        return "통과", "미통과", "-", "-", "-"
    if reason_code == "hold_stage3":
        return "통과", "통과", "미통과", "미통과", "미통과"
    if reason_code == "entry_1_2_3_ok":
        return "통과", "통과", "3차 A안 통과(매수)", "통과", "-"
    if reason_code == "entry_1_2_3_ok_strong":
        return "통과", "통과", "3차 B안 통과(매수)", "-", "통과"
    if reason_code == "hold_no_signal":
        return "(데이터 부족)", "-", "-", "-", "-"
    if reason_code == "hold_event_window":
        return "(이벤트 창)", "-", "-", "-", "-"
    # 매각/기타
    return "-", "-", "(매각/기타)", "-", "-"


def write_engine_responses_markdown(stage_detail: list[dict], output_dir: str, market: str) -> None:
    """응답마다 한 레코드씩 보기 좋게 마크다운으로 저장. 순번·업비트 기준 날짜/시·시스템 시각·1/2/3-1/3-2 스테이지·기타."""
    os.makedirs(output_dir, exist_ok=True)
    path_md = os.path.join(output_dir, "engine_responses_detail.md")
    with open(path_md, "w", encoding="utf-8") as f:
        f.write("# 개미엔진 응답 상세 (판단 횟수별 레코드)\n\n")
        f.write(f"- **종목**: {market}\n")
        f.write(f"- **총 판단 횟수**: {len(stage_detail)}회\n\n")
        f.write("---\n\n")
        for idx, r in enumerate(stage_detail, start=1):
            ts_utc = r.get("timestamp_utc", "")
            # 업비트 데이터 기준: 어느 날짜 몇 시
            upbit_date = ts_utc[:10] if len(ts_utc) >= 10 else ""
            upbit_time = ts_utc[11:19] if len(ts_utc) >= 19 else ts_utc  # HH:MM:SS
            sys_time = r.get("response_time_local", "")  # 우리 시스템 기준 시/분/초
            f.write(f"## 레코드 {idx} (순번 {idx})\n\n")
            f.write("| 구분 | 내용 |\n|------|------|\n")
            f.write(f"| **업비트 데이터 기준** | {upbit_date} **{upbit_time}** (해당 봉 시각) |\n")
            f.write(f"| **우리 시스템 기준 판단 시각** | {sys_time} (시/분/초) |\n")
            f.write(f"| 스텝 | {r.get('step', '')} |\n")
            f.write(f"| 주기(이전 대비) | {r.get('interval_label', '-')} |\n\n")
            f.write("### 스테이지 통과 여부\n\n")
            f.write("| 스테이지 | 통과 여부 |\n|----------|------------|\n")
            f.write(f"| 1스테이지 (국면·슬롯) | {r.get('stage1', '-')} |\n")
            f.write(f"| 2스테이지 (정배열·ADX) | {r.get('stage2', '-')} |\n")
            f.write(f"| 3-1스테이지 (A안 눌림목) | {r.get('stage3_1', '-')} |\n")
            f.write(f"| 3-2스테이지 (B안 강한추세) | {r.get('stage3_2', '-')} |\n\n")
            f.write("### 판단 결과\n\n")
            f.write("| 항목 | 값 |\n|------|-----|\n")
            f.write(f"| 신호 | {r.get('signal', '')} |\n")
            f.write(f"| reason_code | {r.get('reason_code', '')} |\n")
            f.write(f"| 현재가 (원) | {r.get('current_price', 0):,.0f} |\n")
            f.write(f"| 보유 포지션 수 | {r.get('positions_count', 0)} |\n")
            f.write(f"| 잔고 (원) | {r.get('balance_krw', 0):,.2f} |\n")
            f.write(f"| 판단 시각(UTC) | {ts_utc} |\n")
            f.write("\n---\n\n")
    print(f"저장: {path_md}")


def write_report(
    market: str,
    trades: list[dict],
    daily: list[dict],
    engine_responses: list[dict],
    output_dir: str,
    period_from: str | None = None,
    period_to: str | None = None,
) -> None:
    os.makedirs(output_dir, exist_ok=True)

    total_pnl = sum(t.get("pnl_krw", 0) for t in trades if t["side"] == "sell")
    total_pct = 100 * total_pnl / INITIAL_KRW
    buy_count = sum(1 for t in trades if t["side"] == "buy")
    sell_count = sum(1 for t in trades if t["side"] == "sell")
    reason_counts = defaultdict(int)
    for t in trades:
        reason_counts[t["reason_code"]] += 1

    # 스텝별 엔진 판단 + 1·2·3차·3-1·3-2 통과 여부 + 판단 시각·주기
    stage_detail: list[dict] = []
    stage_summary = defaultdict(int)  # hold_stage1, hold_stage2, hold_stage3, entry_*, ...
    for r in engine_responses:
        code = r.get("reason_code") or ""
        s1, s2, s3, s3_1, s3_2 = stage_from_reason(code)
        stage_detail.append({
            "step": r.get("_step"),
            "timestamp_utc": r.get("_t"),
            "current_price": r.get("_price"),
            "signal": r.get("signal", ""),
            "reason_code": code,
            "stage1": s1,
            "stage2": s2,
            "stage3": s3,
            "stage3_1": s3_1,  # 3-1스테이지(A안)
            "stage3_2": s3_2,  # 3-2스테이지(B안)
            "response_time_local": r.get("_response_time_local", ""),
            "response_time_utc": r.get("_response_time_utc", ""),
            "positions_count": r.get("_positions_count", 0),
            "balance_krw": r.get("_balance_krw", 0),
            "interval_sec": None,
            "interval_label": "-",
        })
        if code:
            stage_summary[code] += 1
    # 이전 스텝 대비 주기(간격) 계산
    for i in range(len(stage_detail)):
        if i == 0:
            stage_detail[i]["interval_sec"] = 0
            stage_detail[i]["interval_label"] = "-"
            continue
        prev_ts = _parse_utc_ts(stage_detail[i - 1].get("timestamp_utc") or "")
        curr_ts = _parse_utc_ts(stage_detail[i].get("timestamp_utc") or "")
        if prev_ts and curr_ts:
            sec = (curr_ts - prev_ts).total_seconds()
            stage_detail[i]["interval_sec"] = round(sec, 0)
            stage_detail[i]["interval_label"] = _interval_label(sec)
        else:
            stage_detail[i]["interval_label"] = "-"

    write_engine_responses_markdown(stage_detail, output_dir, market)

    report = {
        "summary": {
            "market": market,
            "initial_krw": INITIAL_KRW,
            "total_realized_pnl_krw": round(total_pnl, 2),
            "total_return_pct": round(total_pct, 4),
            "buy_count": buy_count,
            "sell_count": sell_count,
            "reason_code_counts": dict(reason_counts),
            "stage_summary": dict(stage_summary),
        },
        "daily": daily,
        "trades": trades,
        "stage_detail": stage_detail,
    }

    path_json = os.path.join(output_dir, "backtest_report.json")
    with open(path_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"저장: {path_json}")

    path_md = os.path.join(output_dir, "backtest_report.md")
    with open(path_md, "w", encoding="utf-8") as f:
        f.write("# 개미엔진 업비트 원화 백테스트 결과\n\n")
        f.write(f"- **종목**: {market}\n")
        f.write(f"- **시드**: {INITIAL_KRW:,}원 (100% 자동매매)\n")
        if period_from and period_to:
            f.write(f"- **데이터 기간**: {period_from} ~ {period_to}\n")
        f.write("\n---\n\n")

        # 요약
        f.write("## 1. 요약\n\n")
        f.write("| 항목 | 값 |\n|------|-----|\n")
        f.write(f"| 총 실현 손익 (원) | {total_pnl:,.2f} |\n")
        f.write(f"| 총 수익률 (%) | {total_pct:.4f} |\n")
        f.write(f"| 매수 횟수 | {buy_count} |\n")
        f.write(f"| 매도 횟수 | {sell_count} |\n\n")

        # 진입 3단계 설명
        f.write("## 2. 개미엔진 진입 단계 (3단계)\n\n")
        f.write("| 단계 | 내용 |\n|------|------|\n")
        f.write("| 1차 | 국면 상승 + 보유 슬롯 여유 (max_positions 미만) |\n")
        f.write("| 2차 | 1h 정배열(단기EMA>장기EMA) + 4h 정배열 + ADX≥25 |\n")
        f.write("| 3차 A안 | 눌림목: 가격이 단기EMA 근처, RSI≤50, 거래량≤평균 → 매수 |\n")
        f.write("| 3차 B안 | 강한 추세: market_score≥8, ADX 1h≥35, 4h≥30 → 매수 |\n\n")

        # 거래 로그: 매수종목·매수 시 금액, 매도종목·매도 시 금액 명시
        f.write("## 3. 거래 로그 (매수/매도 종목·금액·엔진 판단)\n\n")
        f.write("체결된 매수/매도마다 **매수 종목·그때 금액**, **매도 종목·그때 금액**을 표시합니다.\n\n")
        f.write("| 시각(UTC) | 구분 | 매수/매도 종목 | 체결금액(원) | 단가 | 수량 | 엔진 판단(reason_code) | 실현손익(원) |\n")
        f.write("|-----------|------|----------------|--------------|------|------|--------------------------|---------------|\n")
        for t in trades:
            side_label = "매수" if t["side"] == "buy" else "매도"
            pnl_str = f"{t.get('pnl_krw', 0):,.2f}" if t["side"] == "sell" else "-"
            f.write(f"| {t['timestamp_utc']} | {side_label} | {t['market']} | {t['amount_krw']:,.2f} | {t['price']:,.0f} | {t['quantity']:.6f} | {t['reason_code']} | {pnl_str} |\n")
        f.write("\n")

        # 일별 수익률
        f.write("## 4. 일별 수익률\n\n")
        f.write("| 날짜 | 일별 손익(원) | 일별 수익률(%) | 누적 손익(원) | 누적 수익률(%) | 거래 수 |\n")
        f.write("|------|---------------|----------------|----------------|----------------|--------|\n")
        for row in daily:
            f.write(f"| {row['date']} | {row['daily_pnl_krw']:,.2f} | {row['daily_pnl_pct']:.4f} | {row['cumulative_pnl_krw']:,.2f} | {row['cumulative_pnl_pct']:.4f} | {row['trades_count']} |\n")
        f.write("\n")

        # 스텝별 엔진 판단 상세 — 판단 주기마다 전부 기록 (이번 판단에서 어디서 미통과했는지·판단 주기 검토용)
        f.write("## 5. 스텝별 엔진 판단 상세 (전체 기록)\n\n")
        f.write("엔진이 **판단하는 주기마다 모두** 기록합니다. 각 스텝에서 **이번 판단은 어디에서 통과를 못했는지**(1차/2차/3차), **판단 주기가 너무 느린지**를 **판단 시각(UTC)**과 **주기(이전 대비)**로 확인할 수 있습니다.\n\n")
        f.write("| 스텝 | 판단 시각(UTC) | 주기(이전 대비) | 현재가 | 신호 | reason_code | 1차 | 2차 | 3-1(A안) | 3-2(B안) |\n")
        f.write("|------|----------------|-----------------|--------|------|-------------|-----|-----|----------|----------|\n")
        for r in stage_detail:
            ts = r.get("timestamp_utc", "")
            interval = r.get("interval_label", "-")
            f.write(f"| {r.get('step', '')} | {ts} | {interval} | {r.get('current_price', 0):,.0f} | {r.get('signal', '')} | {r.get('reason_code', '')} | {r.get('stage1', '')} | {r.get('stage2', '')} | {r.get('stage3_1', '')} | {r.get('stage3_2', '')} |\n")
    print(f"저장: {path_md}")


def main() -> int:
    parser = argparse.ArgumentParser(description="업비트 실데이터 + 개미엔진 모의 백테스트 (시드 100만원)")
    parser.add_argument("--data", default="backtest_data.json", help="캔들 JSON (candles_1h, candles_4h) 또는 없으면 샘플")
    parser.add_argument("--engine-url", default="http://127.0.0.1:9100", help="AntEngine URL")
    parser.add_argument("--output-dir", default="backtest_results", help="결과 저장 디렉터리")
    parser.add_argument("--min-candles", type=int, default=26, help="최소 1h 캔들 수")
    parser.add_argument("--max-steps", type=int, default=None, help="최대 시뮬레이션 스텝 수 (기본 전체)")
    parser.add_argument("--entry-profile", type=int, default=2, choices=(0, 1, 2, 3, 4),
                       help="진입 완화 프로필: 0=기본, 1=ADX22, 2=+3차A완화, 3=+3차B완화, 4=+3차C안 (기본 2)")
    parser.add_argument("--run-all-profiles", action="store_true",
                       help="프로필 1~4 순차 실행 후 수익률 비교 (단일 데이터 파일 기준)")
    args = parser.parse_args()

    if requests is None:
        print("pip install requests 필요", file=sys.stderr)
        return 1

    # 엔진 필수: 연결 확인 후 실패 시 사용자에게 알리고 종료
    if not ensure_engine_running(args.engine_url):
        print("", file=sys.stderr)
        print("개미엔진에 연결할 수 없습니다. 백테스트를 실행할 수 없는 상태입니다.", file=sys.stderr)
        print("", file=sys.stderr)
        print("조치: 아래 중 하나를 진행한 뒤 다시 시도하세요.", file=sys.stderr)
        print("  1) 개미엔진을 수동 실행:", file=sys.stderr)
        print("     - Windows: ant_engine\\build\\ant_engine.exe", file=sys.stderr)
        print("     - Linux:   ./AntEngine-1.0.bin (기본 포트 9100)", file=sys.stderr)
        print("  2) 방화벽/포트 9100 확인", file=sys.stderr)
        print("  3) 다른 주소 사용 시: --engine-url http://호스트:포트", file=sys.stderr)
        print("", file=sys.stderr)
        return 1

    if os.path.isfile(args.data):
        with open(args.data, "r", encoding="utf-8") as f:
            data = json.load(f)
        candles_1h = data.get("candles_1h", [])
        candles_4h = data.get("candles_4h", [])
        market = data.get("market", "KRW-BTC")
        if not candles_1h:
            print("candles_1h 없음", file=sys.stderr)
            return 1
        # 업비트 데이터 결측/공백 검사
        val = validate_candle_data(candles_1h, candles_4h)
        print(f"데이터 검증: 1h {val['1h_count']}개, 4h {val['4h_count']}개 — {val['message']}")
        if not val["ok"]:
            print("  경고: 1h/4h 봉에 공백이 있습니다. 시뮬레이션은 계속 진행합니다.", file=sys.stderr)
    else:
        candles_1h = make_sample_candles_1h(500)
        candles_4h = make_sample_candles_4h_from_1h(candles_1h)
        market = "KRW-BTC"
        print("실제 데이터 없음, 샘플로 실행합니다. --data backtest_data.json 으로 업비트 데이터 사용 권장.")

    if args.run_all_profiles:
        # 프로필 1~4 순차 실행 후 수익률 비교
        results = []
        for prof in (1, 2, 3, 4):
            out_dir = f"{args.output_dir}_p{prof}"
            os.makedirs(out_dir, exist_ok=True)
            print(f"\n--- 진입 프로필 {prof} 실행 중 (출력: {out_dir}) ---")
            run_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            engine_responses, trades, daily = run_simulation(
                args.engine_url, candles_1h, candles_4h, market=market,
                min_candles_1h=args.min_candles, max_steps=args.max_steps, entry_profile=prof,
            )
            run_end = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            total_pnl = sum(t.get("pnl_krw", 0) for t in trades if t["side"] == "sell")
            total_pct = 100.0 * total_pnl / INITIAL_KRW
            buy_count = sum(1 for t in trades if t["side"] == "buy")
            period_from = candles_1h[0]["t"][:10] if candles_1h else None
            period_to = candles_1h[-1]["t"][:10] if candles_1h else None
            write_report(market, trades, daily, engine_responses, out_dir, period_from=period_from, period_to=period_to)
            with open(os.path.join(out_dir, "simulation_run_time.txt"), "w", encoding="utf-8") as f:
                f.write(f"시뮬레이션_시작={run_start}\n시뮬레이션_종료={run_end}\n종목={market}\nentry_profile={prof}\n")
            results.append({"profile": prof, "total_pnl": total_pnl, "total_pct": total_pct, "buy_count": buy_count})
            print(f"  프로필 {prof}: 수익 {total_pnl:,.0f}원 ({total_pct:.4f}%), 매수 {buy_count}회")
        # 비교표 출력 및 최적 프로필
        print("\n=== 진입 프로필 비교 (수익률 기준 최적 = 적용 권장) ===")
        print("| 프로필 | 총 실현손익(원) | 수익률(%) | 매수 횟수 |")
        print("|--------|-----------------|-----------|----------|")
        for r in results:
            print(f"| {r['profile']} | {r['total_pnl']:,.0f} | {r['total_pct']:.4f} | {r['buy_count']} |")
        # 수익률 우선, 동점이면 매수 횟수 많은 쪽, 그다음 프로필 2(진입 기회 확대) 우선
        best = max(
            results,
            key=lambda x: (round(x["total_pct"], 6), x["buy_count"], 1 if x["profile"] == 2 else 0),
        )
        print(f"\n권장 적용: 프로필 {best['profile']} (수익률 {best['total_pct']:.4f}%, 매수 {best['buy_count']}회)")
        return 0

    print("개미엔진 연결 확인됨.")
    print(f"시드: {INITIAL_KRW:,}원 (100% 자동매매), 종목: {market}, 진입 프로필: {args.entry_profile}")
    print(f"1h 봉: {len(candles_1h)}개, 4h 봉: {len(candles_4h)}개")
    print("시뮬레이션 중...")
    run_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    engine_responses, trades, daily = run_simulation(
        args.engine_url,
        candles_1h,
        candles_4h,
        market=market,
        min_candles_1h=args.min_candles,
        max_steps=args.max_steps,
        entry_profile=args.entry_profile,
    )
    print(f"거래 수: 매수 {sum(1 for t in trades if t['side']=='buy')}회, 매도 {sum(1 for t in trades if t['side']=='sell')}회")
    total_pnl = sum(t.get("pnl_krw", 0) for t in trades if t["side"] == "sell")
    print(f"총 실현 손익: {total_pnl:,.2f}원 ({100*total_pnl/INITIAL_KRW:.4f}%)")

    run_end = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    period_from = candles_1h[0]["t"][:10] if candles_1h else None
    period_to = candles_1h[-1]["t"][:10] if candles_1h else None
    write_report(market, trades, daily, engine_responses, args.output_dir, period_from=period_from, period_to=period_to)
    os.makedirs(args.output_dir, exist_ok=True)
    with open(os.path.join(args.output_dir, "simulation_run_time.txt"), "w", encoding="utf-8") as f:
        f.write(f"시뮬레이션_시작={run_start}\n시뮬레이션_종료={run_end}\n종목={market}\nentry_profile={args.entry_profile}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
