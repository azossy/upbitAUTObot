# 개미엔진 (AntEngine)

**엔진명**: 개미엔진 (AntEngine)  
**현재 버전**: 0.9  
**목적**: 트레이딩 기획(트레이딩_엔진_상세_기획서, 입출력_연동_가이드)을 토대로 **별도 바이너리**로 동작하는 시그널 엔진. 속도·최신 기법을 고려해 **C++17**로 구현하며, 단일 실행 파일로 배포한다.

---

## 1. 버전·스키마

| 항목 | 값 |
|------|-----|
| 엔진 버전 | 0.9 |
| 입출력 스키마 버전 | 1.0 |
| 구현 언어 | C++17 (단일 바이너리, CMake 빌드) |

---

## 2. 프로젝트 위치·빌드

- **경로**: 프로젝트 루트의 `ant_engine/`
- **빌드**: `cd ant_engine && mkdir build && cd build && cmake .. && cmake --build . --config Release`  
  - Windows: 실행 파일 `build/Release/ant_engine.exe`  
  - Linux/macOS: `build/ant_engine`
- **실행**: `./ant_engine` 또는 `ant_engine.exe` (기본 포트 9100). 포트 변경 시 환경 변수 `ANT_ENGINE_PORT`
- **의존성**: nlohmann/json, cpp-httplib — CMake FetchContent로 자동 다운로드

---

## 3. API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | /health | 헬스체크. 백엔드·호출 측에서 엔진 기동 여부 확인용. |
| GET | /version | `engine`, `version`, `schema_version` 반환. 연동 전 스키마 확인용. |
| POST | /signal | 시그널 요청. Body는 [트레이딩_엔진_입출력_연동_가이드.md](트레이딩_엔진_입출력_연동_가이드.md) §2 입력값(JSON), 응답은 §3 출력값(JSON). |

---

## 4. v0.9 동작 요약

- **입력 검증**: `market`, `mode` 필수. 형식 오류 시 `status: "error"`, `error_code`·`error_message` 반환.
- **이벤트 창**: `config.event_window_active == true` 이면 진입 보류 → `signal: "hold"`, `reason_code: "hold_event_window"`.
- **매각 판단**: `positions` 중 해당 `market` 포지션에 대해 현재가 기준 손절(`stop_loss_pct`)/익절(`take_profit_pct`) 충족 시 `signal: "sell"`, `reason_code: "exit_stop_loss"` 또는 `"exit_take_profit"`.
- **진입 판단**: `candles_1h` 24개 미만이면 보류. 24개 이상이어도 v0.9에서는 **1차·2차·3차 로직 골격만** 두고, 현재는 `hold_no_signal` 반환. (추후 기획서 §4·§5에 따라 EMA·ADX·RSI·시장 국면 등 확장.)

---

## 5. 관련 문서

- [트레이딩_엔진_상세_기획서.md](트레이딩_엔진_상세_기획서.md) — 기획·팩터·바이너리 분리(§7)
- [트레이딩_엔진_입출력_연동_가이드.md](트레이딩_엔진_입출력_연동_가이드.md) — **입력값 리스트·출력값 리스트**·엔진만 사용 시 연동(코딩) 방법
- [트레이딩기법_연구자료.md](트레이딩기법_연구자료.md) — 연구·기법·가설

---

## 6. 백엔드 연동 (추후)

배짱이 백엔드(FastAPI)에서 봇 실행 시:

1. 엔진 프로세스 기동(또는 이미 떠 있는 엔진 사용).
2. 주기적으로 캔들·포지션·잔고·설정을 수집해 **입출력 가이드 §2** 형태로 JSON 구성.
3. `POST http://127.0.0.1:9100/signal` 호출.
4. 응답 §3에 따라 `signal`이 `buy`/`sell`이면 주문 실행, `hold`면 대기.

엔진 소스는 공개하지 않고 **바이너리만** 배포하는 정책은 유지한다.
