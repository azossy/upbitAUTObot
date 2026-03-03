# 파일명: test.py
# VS Code에서 새 파일 만들기: Ctrl+N → Ctrl+S → test.py

# pyupbit이 정상 설치됐는지 확인
import pyupbit

# 비트코인 현재가 조회
price = pyupbit.get_current_price("KRW-BTC")
print(f"비트코인 현재가: {price:,}원")

# 이더리움 현재가 조회
eth_price = pyupbit.get_current_price("KRW-ETH")
print(f"이더리움 현재가: {eth_price:,}원")

# 업비트 전체 마켓 목록
markets = pyupbit.get_tickers(fiat="KRW")
print(f"KRW 마켓 코인 수: {len(markets)}개")
print(f"처음 5개: {markets[:5]}")