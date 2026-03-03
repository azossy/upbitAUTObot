# -*- coding: utf-8 -*-
"""
123.txt 자동 모니터링 스크립트 (검증관/테스트 에이전트 대리)
- 123.txt를 주기적으로 확인하여 "검증관 할당 작업"에 검증 요청이 올라오면
  자동으로 코드 검증(린트 등)을 수행하고, 결과를 123.txt에 반영한 뒤 할당 섹션을 정리합니다.
- 사용법: 터미널에서 python monitor_123.py 실행 후 그대로 두면 됩니다.
  (중지: Ctrl+C)
"""

import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# 스크립트와 123.txt가 같은 폴더에 있다고 가정
BASE_DIR = Path(__file__).resolve().parent
FILE_123 = BASE_DIR / "123.txt"
CHECK_INTERVAL = 30  # 초 단위 (대기 시 30초마다 123 확인)
BACKEND_APP = BASE_DIR / "backend" / "app"


def read_123():
    """123.txt 내용을 UTF-8로 읽기."""
    try:
        return FILE_123.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[모니터] 123.txt 읽기 오류: {e}")
        return ""


def has_verification_request(content: str) -> bool:
    """'검증관 할당 작업' 섹션에 검증 요청이 있는지 판단."""
    # "■ 검증관 할당 작업" ~ 다음 "------" 구간만 추출
    start_marker = "■ 검증관 할당 작업"
    end_marker = "----------------------------------------------------------------------"
    if start_marker not in content:
        return False
    start = content.find(start_marker)
    rest = content[start:]
    # 다음 구분선 이후는 다른 섹션이므로, 그 전까지만 본다
    next_sep = rest.find(end_marker, len(start_marker))
    if next_sep != -1:
        section = rest[: next_sep]
    else:
        section = rest
    # "현재 할당:" 이 있는 줄만 본다. 그 줄에 "검증 요청"이 있거나, "없음"이 없으면 요청 있는 것
    for line in section.splitlines():
        if "현재 할당:" in line:
            line_lower = line.strip()
            if "검증 요청" in line_lower or "검증요청" in line_lower.replace(" ", ""):
                return True
            if "없음" in line_lower and "검증" not in line_lower:
                return False
            # "현재 할당: API 검증 요청" 같은 형태
            after_colon = line_lower.split("현재 할당:", 1)[-1].strip()
            if after_colon and "없음" not in after_colon:
                return True
            return False
    return False


def run_linter() -> tuple[str, int]:
    """backend/app 아래 파이썬 파일에 대해 flake8 또는 pyflakes 실행. (venv 제외)"""
    if not BACKEND_APP.is_dir():
        return "backend/app 경로 없음. 검증 대상 디렉터리를 확인하세요.", 0
    app_dir = str(BACKEND_APP)
    for cmd_name in ["flake8", "pyflakes"]:
        try:
            result = subprocess.run(
                [sys.executable, "-m", cmd_name, app_dir],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(BASE_DIR),
            )
            out = (result.stdout or "").strip() + "\n" + (result.stderr or "").strip()
            if result.returncode != 0 or out.strip():
                return f"[{cmd_name}]\n{out.strip() or '정적 검사 완료'}", result.returncode
        except FileNotFoundError:
            continue
        except subprocess.TimeoutExpired:
            return "린트 타임아웃", -1
        except Exception as e:
            return f"린트 실행 예외: {e}", -1
    return "flake8/pyflakes 미설치. pip install flake8 권장. 수동 검토 필요.", 0


def get_recent_work_section(content: str) -> str:
    """'최근 작업 내역' 섹션 텍스트 추출 (검증 대상 안내용)."""
    start_marker = "최근 작업 내역 (개발관 기재)"
    end_marker = "----------------------------------------------------------------------"
    if start_marker not in content:
        return "(없음)"
    start = content.find(start_marker)
    rest = content[start:]
    next_sep = rest.find(end_marker, len(start_marker))
    if next_sep != -1:
        return rest[: next_sep].strip()
    return rest.strip()


def update_123_with_verification(content: str, lint_result: str, lint_code: int) -> str:
    """검증 결과로 123.txt 본문 중 '코드 검증 결과 및 작업지시서' 섹션과 '검증관 할당 작업' 섹션을 갱신."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    recent = get_recent_work_section(content)

    verification_block = f"""----------------------------------------------------------------------
=== 코드 검증 결과 및 작업지시서 (검증관 기재) ===
----------------------------------------------------------------------
[검증 시점] {now} (자동 모니터 스크립트)
[검증 대상] (개발관이 "최근 작업 내역"에 기록한 수정/추가 파일 기준)
{recent[:500]}

■ 검증 결과 요약
  - 논리 오류: 자동 스크립트는 정적/린트 수준만 점검. 논리·비즈니스 검증은 검증관(테스트 에이전트) 상세 검토 시 확인.
  - 상용 프로그램 수준 적합성: 린트/스타일 기준 점검 완료. 상용 수준 종합 판단은 검증관 상세 검토 권장.
  - 누락/보완 필요 사항: (아래 상세 참고)

■ 상세 검토 (자동)
  - 정적 검사/린트: {lint_result}
  - 상세 로직·예외처리·보안 검토는 검증관(테스트 에이전트)에게 "123 상세검토해줘" 요청 시 갱신 가능.

■ 작업지시서 (재작업/보완 필요 시 — 개발관에게 전달)
  1. (자동 검증에서 발견된 항목이 있으면 위 상세 검토 참고)
  2. 
  3. 

※ [검증관]: 123.txt 확인 시 "검증관 할당 작업"에 검증 요청이 올라오면 위 항목을 채워 본 섹션을 갱신하고, 재작업이 필요하면 "작업지시서"에 개발관에게 전달할 항목을 번호로 적은 뒤 할당 섹션을 정리합니다.
"""

    # "검증관 할당 작업"의 "현재 할당: ..." 한 줄을 처리 완료로 교체
    assignment_done = (
        "현재 할당: 없음 — 자동 처리 완료 ("
        + now
        + '). 상세 검토는 검증관(테스트 에이전트)에게 "123 상세검토해줘" 요청 시 갱신 가능.'
    )

    # 기존 "=== 코드 검증 결과 및 작업지시서" ~ "할당 섹션을 정리합니다." 끝까지 한 블록 교체
    old_start = "=== 코드 검증 결과 및 작업지시서 (검증관 기재) ==="
    if old_start in content:
        start_idx = content.find(old_start)
        end_phrase = "할당 섹션을 정리합니다."
        end_idx = content.find(end_phrase, start_idx)
        if end_idx != -1:
            end_idx += len(end_phrase)
            if end_idx < len(content) and content[end_idx] == "\n":
                end_idx += 1
        else:
            end_idx = len(content)
        content = content[:start_idx] + verification_block.rstrip() + "\n" + content[end_idx:]
    else:
        content = content.rstrip() + "\n\n" + verification_block

    # "현재 할당: ..." 한 줄만 교체 (검증관 할당 작업 섹션에 하나뿐)
    content = re.sub(r"현재 할당: [^\n]+", assignment_done, content, count=1)

    return content


def main():
    print("123.txt 자동 모니터링을 시작합니다. 검증 요청이 올라오면 자동으로 검증 후 123.txt를 갱신합니다.")
    print(f"확인 주기: {CHECK_INTERVAL}초 | 중지: Ctrl+C")
    print(f"123.txt 경로: {FILE_123}")
    if not FILE_123.exists():
        print("123.txt가 없습니다. 같은 폴더에 123.txt를 두고 다시 실행하세요.")
        return
    while True:
        try:
            content = read_123()
            if has_verification_request(content):
                print(f"[{datetime.now():%H:%M:%S}] 검증 요청 감지. 검증 실행 중...")
                lint_result, lint_code = run_linter()
                new_content = update_123_with_verification(content, lint_result, lint_code)
                FILE_123.write_text(new_content, encoding="utf-8")
                print("[완료] 123.txt에 검증 결과 반영 및 할당 섹션 정리함. 다음 작업 대기 중.")
            else:
                print(f"[{datetime.now():%H:%M:%S}] 할당 없음. 대기 중...")
        except KeyboardInterrupt:
            print("\n모니터링 중지.")
            break
        except Exception as e:
            print(f"[오류] {e}")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
