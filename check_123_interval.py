#!/usr/bin/env python3
"""
모든 에이전트 대기 루프용: 10초마다 123(화이트보드) 확인 안내를 출력합니다.
이 스크립트를 실행해 두고, 출력되는 시점에 채팅에 "123 확인"을 입력하면
코딩 에이전트가 123.md(화이트보드)를 확인하고 새 작업이 있으면 수행 후 결과를 123에 업데이트합니다.

123 = 화이트보드 = 프로젝트 루트의 123.md
사용법: python check_123_interval.py
종료: Ctrl+C
"""

import time
import sys
from datetime import datetime

def main():
    print("모든 에이전트 10초마다 123 확인 안내를 시작합니다. (종료: Ctrl+C)\n", flush=True)
    n = 0
    while True:
        n += 1
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] #{n} — 123(화이트보드) 확인해 주세요. (채팅에 '123 확인' 입력)", flush=True)
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            print("\n종료했습니다.", flush=True)
            sys.exit(0)

if __name__ == "__main__":
    main()
