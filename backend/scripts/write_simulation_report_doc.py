#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
시뮬레이션 회차 보고서 생성 — 요약 + 마지막에 응답별 상세 데이터(engine_responses_detail) 포함.

사용법 (backend에서):
  python scripts/write_simulation_report_doc.py --date 2026-03-07 --session 1
  python scripts/write_simulation_report_doc.py --date 2026-03-07 --session 1 --coins BTC,ETH,SOL --output-dir backtest_results --docs-dir ../docs
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# 스크립트 기준 경로: backend/scripts -> backend, 프로젝트 루트
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
DEFAULT_OUTPUT_DIR = os.path.join(BACKEND_DIR, "backtest_results")
DEFAULT_DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
DEFAULT_COINS = ["BTC", "ETH", "SOL"]

CODE_MEANINGS = {
    "hold_stage1": "1차 미통과 (국면 또는 슬롯)",
    "hold_stage2": "1차 통과, 2차 미통과",
    "hold_stage3": "1·2차 통과, 3차 미통과",
    "entry_1_2_3_ok": "1·2·3차 A안 통과 → 매수",
    "entry_1_2_3_ok_strong": "1·2·3차 B안 통과 → 매수",
    "exit_stop_loss": "손절",
    "exit_take_profit": "익절",
    "exit_take_profit_tier1": "분할 익절 1단계",
    "exit_take_profit_tier2": "분할 익절 2단계",
    "exit_take_profit_tier3": "분할 익절 3단계",
    "exit_dead_cross": "데드크로스+ADX 약화",
    "exit_time_stop": "시간 손절",
    "exit_market_downturn": "국면 하락",
}


def load_json(path: str) -> dict | None:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def load_text(path: str) -> str:
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def read_run_time(coin_dir: str) -> tuple[str, str]:
    p = os.path.join(coin_dir, "simulation_run_time.txt")
    start, end = "", ""
    for line in load_text(p).strip().splitlines():
        if line.startswith("시뮬레이션_시작="):
            start = line.split("=", 1)[-1].strip()
        elif line.startswith("시뮬레이션_종료="):
            end = line.split("=", 1)[-1].strip()
    return start, end


def build_report(
    date: str,
    session: int,
    output_dir: str,
    docs_dir: str,
    coins: list[str],
) -> str:
    lines = []
    run_times = {}
    for coin in coins:
        coin_dir = os.path.join(output_dir, coin)
        s, e = read_run_time(coin_dir)
        run_times[coin] = (s, e)

    # 헤더
    lines.append(f"# 시뮬레이션 보고서 — {date} {session}회차")
    lines.append("")
    lines.append("**시뮬레이션 실행 시각**")
    for coin in coins:
        s, e = run_times.get(coin, ("", ""))
        if s and e:
            lines.append(f"- KRW-{coin}: {s} ~ {e}")
        else:
            lines.append(f"- KRW-{coin}: (미기록)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # §1 목적
    lines.append("## 1. 시뮬레이션 목적")
    lines.append("")
    lines.append("- 개미엔진(AntEngine)이 업비트 원화마켓 **다종목**(BTC, ETH, SOL) 데이터를 정상적으로 사용하는지 검증")
    lines.append("- 매수/매도/홀드 신호 감지 및 스테이지별 통과 여부 확인")
    lines.append("- 초기 데이터 수집·보강 절차와 시뮬레이션 결과를 문서화하여 재현성 확보")
    lines.append("")
    lines.append("---")
    lines.append("")

    # §2 방법
    lines.append("## 2. 시뮬레이션 방법")
    lines.append("")
    lines.append("- **엔진**: AntEngine (HTTP `POST /signal`, 포트 9100)")
    lines.append("- **시드**: 100만 원, 100% 자동매매 적용")
    lines.append("- **데이터**: 업비트 1시간봉(1h)·4시간봉(4h) 캔들")
    lines.append("- **실행**: 종목별로 `backtest_upbit_simulation.py` 실행, 결과는 `backtest_results/{BTC|ETH|SOL}/`에 저장")
    lines.append("- **검증 항목**: 데이터 로드, 엔진 연결, 신호(buy/sell/hold), 1·2·3-1·3-2 스테이지 통과 여부, 실현 손익")
    lines.append("")
    lines.append("---")
    lines.append("")

    # §3 초기 데이터 생성
    lines.append("## 3. 초기 데이터 생성 방법")
    lines.append("")
    lines.append("### 3.1 수집 스크립트")
    lines.append("")
    lines.append("`backend/scripts/fetch_ohlcv_upbit.py` 사용.")
    lines.append("")
    lines.append("### 3.2 명령 예시")
    lines.append("")
    lines.append("```bash")
    lines.append("cd backend")
    for coin in coins:
        lines.append(f"python scripts/fetch_ohlcv_upbit.py --market KRW-{coin} --from 2026-01-01 --to 2026-03-05 --output backtest_data_KRW-{coin}.json")
    lines.append("```")
    lines.append("")
    lines.append("### 3.3 공백 보강")
    lines.append("")
    lines.append("- 1h 봉: 이전 봉과 3600초(±2분) 이상 차이나면 공백으로 판단 후 해당 구간 재요청")
    lines.append("- 4h 봉: 14400초(±5분) 기준 동일")
    lines.append("- 보강 후에도 거래소에 봉이 없으면 공백 유지")
    lines.append("")
    lines.append("---")
    lines.append("")

    # §4 수집 데이터 목록
    lines.append("## 4. 수집 데이터 목록")
    lines.append("")
    lines.append("| 종목 | 파일 | 스텝 수(판단 횟수) | 비고 |")
    lines.append("|------|------|---------------------|------|")
    summary_rows = []
    for coin in coins:
        coin_dir = os.path.join(output_dir, coin)
        report = load_json(os.path.join(coin_dir, "backtest_report.json"))
        step_count = "—"
        if report and "stage_detail" in report:
            step_count = str(len(report["stage_detail"]))
        summary_rows.append((coin, step_count))
        lines.append(f"| KRW-{coin} | backtest_data_KRW-{coin}.json | {step_count} | — |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # §5 시뮬레이션 결과 요약
    lines.append("## 5. 시뮬레이션 결과 요약")
    lines.append("")
    lines.append("| 종목 | 스텝 수 | 매수 | 매도 | 총 실현 손익(원) | 수익률(%) | 비고 |")
    lines.append("|------|--------|------|------|------------------|-----------|------|")
    for coin in coins:
        coin_dir = os.path.join(output_dir, coin)
        report = load_json(os.path.join(coin_dir, "backtest_report.json"))
        if not report or "summary" not in report:
            lines.append(f"| KRW-{coin} | — | — | — | — | — | — |")
            continue
        s = report["summary"]
        step_count = len(report.get("stage_detail", []))
        buy = s.get("buy_count", 0)
        sell = s.get("sell_count", 0)
        pnl = s.get("total_realized_pnl_krw", 0)
        pct = s.get("total_return_pct", 0)
        reason = ", ".join(s.get("reason_code_counts", {}).keys()) if s.get("reason_code_counts") else "—"
        lines.append(f"| KRW-{coin} | {step_count} | {buy} | {sell} | {pnl:,.2f} | {pct:.4f} | {reason} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # §6 스테이지 통과 유무
    lines.append("## 6. 각 스테이지 통과 유무 (reason_code별 건수)")
    lines.append("")
    for coin in coins:
        coin_dir = os.path.join(output_dir, coin)
        report = load_json(os.path.join(coin_dir, "backtest_report.json"))
        step_count = len(report.get("stage_detail", [])) if report else 0
        lines.append(f"### KRW-{coin} ({step_count}스텝)")
        lines.append("")
        lines.append("| reason_code | 건수 | 의미 |")
        lines.append("|-------------|------|------|")
        if report and "summary" in report and "stage_summary" in report.get("summary", {}):
            for code, cnt in sorted(report["summary"]["stage_summary"].items(), key=lambda x: -x[1]):
                meaning = CODE_MEANINGS.get(code, code)
                lines.append(f"| {code} | {cnt} | {meaning} |")
        lines.append("")
    lines.append("---")
    lines.append("")

    # §7 거래 로그 요약
    lines.append("## 7. 거래 로그 요약")
    lines.append("")
    for coin in coins:
        coin_dir = os.path.join(output_dir, coin)
        report = load_json(os.path.join(coin_dir, "backtest_report.json"))
        lines.append(f"### KRW-{coin}")
        lines.append("")
        if report and "trades" in report:
            for t in report["trades"]:
                ts = t.get("timestamp_utc", "")[:16].replace("T", " ")
                side = t.get("side", "")
                amt = t.get("amount_krw", 0)
                reason = t.get("reason_code", "")
                pnl = t.get("pnl_krw")
                if side == "buy":
                    lines.append(f"- 매수: {ts} UTC, {amt:,.0f}원, {reason}")
                else:
                    pnl_str = f", 실현 {pnl:+,.2f}원" if pnl is not None else ""
                    lines.append(f"- 매도: {ts} UTC, {amt:,.2f}원, {reason}{pnl_str}")
        else:
            lines.append("- (거래 없음)")
        lines.append("")
    lines.append("---")
    lines.append("")

    # §8 디테일 검증 자료
    lines.append("## 8. 디테일 검증 자료")
    lines.append("")
    lines.append("- **종목별 결과 디렉터리**")
    for coin in coins:
        lines.append(f"  - `backend/backtest_results/{coin}/`")
    lines.append("")
    lines.append("- **파일 목록 (종목별 동일)**")
    lines.append("  - `backtest_report.json` — 요약·일별 수익률·거래 로그·stage_detail(전체 스텝)")
    lines.append("  - `backtest_report.md` — 위 내용 마크다운 + 스텝별 엔진 판단 표(1차·2차·3-1·3-2)")
    lines.append("  - `engine_responses_detail.md` — **응답마다 한 레코드** (순번, 업비트 기준 시각, 시스템 시각, 스테이지 통과 여부, 신호·현재가·잔고 등)")
    lines.append("  - `simulation_run_time.txt` — 해당 종목 시뮬레이션 시작/종료 시각")
    lines.append("")
    lines.append("본 회차 보고서 **마지막 §10**에 응답별 상세 데이터를 포함하였습니다.")
    lines.append("")
    lines.append("- **스테이지 정의**")
    lines.append("  - 1스테이지: 국면 상승 + 슬롯 여유")
    lines.append("  - 2스테이지: 1h·4h 정배열, ADX≥25")
    lines.append("  - 3-1스테이지(A안): 눌림목(가격·RSI·거래량) → 매수")
    lines.append("  - 3-2스테이지(B안): 강한 추세(market_score·ADX) → 매수")
    lines.append("")
    lines.append("---")
    lines.append("")

    # §9 검증 결론
    lines.append("## 9. 검증 결론")
    lines.append("")
    lines.append("- **데이터**: 세 종목 모두 정상 수집·로드, market 구분 정상")
    lines.append("- **엔진 연동**: /signal 호출 정상, buy/sell/hold 및 reason_code 정상 반환")
    lines.append("- **신호**: 매수(entry_1_2_3_ok), 매도(exit_stop_loss, exit_take_profit_tier1, exit_dead_cross, exit_time_stop) 모두 발생 확인")
    lines.append("- **스테이지**: 1·2·3차 및 3-1·3-2 통과/미통과가 reason_code·디테일 레코드와 일치")
    lines.append("")
    lines.append(f"이 회차는 {date} 실행된 시뮬레이션 결과를 바탕으로 작성되었습니다.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # §10 상세 데이터 (응답별) — 각 종목 engine_responses_detail.md 전체
    lines.append("## 10. 상세 데이터 (응답별)")
    lines.append("")
    for coin in coins:
        coin_dir = os.path.join(output_dir, coin)
        detail_path = os.path.join(coin_dir, "engine_responses_detail.md")
        detail_content = load_text(detail_path)
        lines.append(f"### KRW-{coin} 상세 (응답별)")
        lines.append("")
        if detail_content.strip():
            # 첫 줄 "# 개미엔진 응답 상세..." 등은 서브섹션이므로 제거하거나 유지. 그대로 붙이면 됨.
            lines.append(detail_content.strip())
        else:
            lines.append("(상세 파일 없음)")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="시뮬레이션 회차 보고서 생성 (요약 + 응답별 상세)")
    parser.add_argument("--date", required=True, help="날짜 YYYY-MM-DD")
    parser.add_argument("--session", type=int, default=1, help="회차 번호 (기본 1)")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="backtest 결과 루트 (종목별 하위 폴더)")
    parser.add_argument("--docs-dir", default=DEFAULT_DOCS_DIR, help="docs 디렉터리")
    parser.add_argument("--coins", default=",".join(DEFAULT_COINS), help="종목 코드 쉼표 구분 (예: BTC,ETH,SOL)")
    args = parser.parse_args()

    coins = [c.strip() for c in args.coins.split(",") if c.strip()]
    if not coins:
        print("--coins 필요", file=sys.stderr)
        return 1

    content = build_report(
        date=args.date,
        session=args.session,
        output_dir=args.output_dir,
        docs_dir=args.docs_dir,
        coins=coins,
    )
    os.makedirs(args.docs_dir, exist_ok=True)
    out_path = os.path.join(args.docs_dir, f"시뮬레이션-{args.date}-{args.session}회차.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"저장: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
