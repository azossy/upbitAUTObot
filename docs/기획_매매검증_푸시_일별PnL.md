# 배짱이 v1.0 — 기획: 매매 검증 · 푸시 알림 · 일별 PnL

**저작자**: 차리 (challychoi@me.com)  
**작성**: 기획관(P에이전트)  
**근거**: PRD, 현재 구현(backend/Flutter), upbit-trading-system 참조  
**목적**: 개발관 작업 지시·검증관 검증 시 사용할 상세 기획

---

## 1. 실제 매매 로직 검증 (봇 시작 시 업비트 API 실제 동작 여부)

### 1.1 현재 상태

- **backend**: `POST /api/v1/bot/start` 호출 시 `bot.status = RUNNING`으로만 변경 후 DB 커밋. **실제 트레이딩 엔진이 기동되지 않음.** (업비트 API 호출 없음)
- **참조**: `upbit-trading-system/backend`에는 `TradingStrategy`, `OrderExecutor`, `UpbitClient` 등이 있으나, 현재 프로젝트 `backend`에는 트레이딩 런타임이 없음.

### 1.2 기획 목표

- 봇 "시작" 시 **실제로 업비트 API를 사용하는 트레이딩 사이클**이 동작하는지 검증 가능하게 한다.
- 검증 관점: (1) 봇 시작 시 엔진 기동 여부 (2) 주문/취소/잔고 조회 등 API 호출 성공 여부 (3) 테스트 시 자금 안전(소액 또는 테스트넷 활용).

### 1.3 구현 방향 (개발관 참고)

| 구분 | 내용 |
|------|------|
| **엔진 기동** | 봇 시작 시 트레이딩 엔진을 기동할 수단 필요. 선택지: (A) FastAPI 백그라운드 asyncio 태스크, (B) Celery 비동기 태스크, (C) 별도 워커 프로세스. **1차 권장**: (A) — 앱 라이프사이클 내에서 `asyncio.create_task(trading_loop(bot_id, user_id))` 등으로 루프 실행. 봇 정지 시 해당 태스크 종료. |
| **트레이딩 로직 위치** | `upbit-trading-system`의 `app/trading/`(strategy, order_executor, upbit_client 등)를 현재 `backend/app/trading/`으로 이식하거나, 최소한 **주문 1회 시도(예: 최소 금액 매수/즉시 취소)** 수준의 검증용 플로우를 현재 backend에 구현. |
| **검증용 모드** | 가능하면 **실제 주문 없이** 업비트 API 연결·잔고 조회만 하는 "검증 모드" 또는 **매우 소액** 한 번만 주문 후 취소하는 시나리오를 문서화. (실제 매매는 사용자 책임으로 안내.) |
| **로그/상태** | 봇 상태가 ERROR일 때 사유 저장, API 호출 실패 시 로그에 기록해 검증 시 확인 가능하게. |

### 1.4 검증 체크리스트 (검증관 참고)

- [ ] 봇 시작 API 호출 후, 백엔드 로그 또는 상태에서 "업비트 API 호출(잔고 조회 또는 주문 시도)" 이력이 있는가?
- [ ] 봇 정지 시 실행 중인 트레이딩 루프/태스크가 정상 종료되는가?
- [ ] API 키 미등록/잘못된 키 시 400 등 적절한 에러와 메시지가 반환되는가?

---

## 2. 푸시 알림 연동 (텔레그램 / FCM — 매수·매도·손절 알림)

### 2.1 현재 상태

- **설정**: 사용자별 `telegram_chat_id` 저장·조회·수정 가능 (설정 화면, `PUT /api/v1/bot/config`).
- **백엔드**: 알림을 **발송하는 코드 없음**. 매매 체결/손절/긴급정지 시점에 푸시를 보내는 로직이 없음.
- **참조**: `upbit-trading-system/backend/app/trading/telegram_notifier.py`에 `TelegramNotifier`(매수/매도/손절/에러 알림) 구현됨. 환경변수 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_DEFAULT_CHAT_ID` 사용.

### 2.2 기획 목표

- **텔레그램**: 매수 체결, 매도 체결, 손절, 긴급 정지 시 사용자 `telegram_chat_id`로 알림 발송.
- **FCM**(선택): 앱 푸시(매수/매도/손절/긴급정지). FCM 토큰 등록 API·발송 로직은 2차로 두고, 1차는 텔레그램만 구현해도 무방.

### 2.3 구현 방향 (개발관 참고)

| 구분 | 내용 |
|------|------|
| **텔레그램 1차** | 1) `backend`에 텔레그램 발송 모듈 추가(또는 upbit-trading-system의 `TelegramNotifier` 이식). 2) **발송 시점**: 실제 매매 로직이 있는 곳(주문 체결 후, 손절 실행 후, 긴급 정지 시)에서 해당 유저의 `telegram_chat_id`를 DB에서 조회 후 발송. 3) `telegram_chat_id`가 없으면 건너뜀. 4) 환경변수: `TELEGRAM_BOT_TOKEN`(봇 토큰), 사용자별 채팅 ID는 DB `user.telegram_chat_id` 사용. |
| **알림 유형** | PRD 기준: 매수 체결(PUSH-01), 매도 체결(PUSH-02), 손절(PUSH-03), 긴급 정지(PUSH-04). 메시지에 코인·가격·금액·손익 등 최소 정보 포함. |
| **FCM 2차** | Flutter에서 FCM 토큰 발급 후 서버에 등록(예: `PUT /api/v1/me/fcm-token`). 서버에서 Firebase Admin SDK로 발송. 1차 기획에서는 텔레그램만 명시해도 됨. |

### 2.4 검증 체크리스트 (검증관 참고)

- [ ] 텔레그램 봇 토큰·채팅 ID 설정 시, (테스트용) 매수/매도/손절 시뮬레이션 또는 실제 이벤트에서 해당 채팅으로 메시지가 도착하는가?
- [ ] `telegram_chat_id`가 비어 있으면 발송 시도 없이 건너뛰는가?
- [ ] 메시지 내용에 코인·가격 등 필수 정보가 포함되는가?

---

## 3. 일별 수익 시계열 API (백엔드 PnL 이력 → 차트 확장)

### 3.1 현재 상태

- **백엔드**: `GET /api/v1/bot/status`에서 `total_pnl`, `daily_pnl`, `weekly_pnl` 단일 값만 반환. **일별 시계열 API 없음.**
- **Flutter**: `PnlChart`가 `dailyPnl`, `weeklyPnl` 두 개 막대만 표시. 일별 추이 라인/막대 없음.
- **데이터**: `Trade` 테이블에 `realized_pnl`, `realized_pnl_pct`, `created_at` 있음. 일별 집계 가능.

### 3.2 기획 목표

- 백엔드에서 **일별 수익률(또는 손익금) 이력**을 반환하는 API 제공.
- Flutter 대시보드에서 **일별 수익 추이**를 차트(라인 또는 막대)로 표시.

### 3.3 구현 방향 (개발관 참고)

| 구분 | 내용 |
|------|------|
| **API** | `GET /api/v1/bot/pnl-history?days=30` (또는 `period=7d|30d|90d`). 응답: `[{ "date": "2025-03-01", "pnl": 1.5, "pnl_krw": 50000 }]` 형태. `date`는 KST 기준 일(YYYY-MM-DD) 권장. |
| **집계** | `Trade` 테이블에서 `user_id` 일치, `created_at`을 일별로 그룹핑 후 `realized_pnl` 합산. 해당 일에 거래 없으면 `pnl: 0`(또는 누락)으로 포함. 기간은 `days` 파라미터(기본 30일)만큼 과거. |
| **Flutter** | `api_service`에 `getPnlHistory(days)` 추가. 대시보드 또는 설정 근처에서 호출 후, `PnlChart` 확장 또는 새 위젯(예: `PnlHistoryChart`)에서 일별 데이터로 라인/막대 차트 표시. One UI·기존 카드 스타일 유지. |

### 3.4 검증 체크리스트 (검증관 참고)

- [ ] `GET /api/v1/bot/pnl-history?days=30` 응답이 `[{ date, pnl, ... }]` 형식이며, `Trade` 데이터와 일치하는가?
- [ ] Flutter에서 해당 API 호출 후 차트에 일별 데이터가 반영되는가?
- [ ] 거래가 없는 날은 0 또는 빈 값으로 처리되어 차트가 깨지지 않는가?

---

## 4. 우선순위 및 작업 순서 제안

| 순서 | 항목 | 비고 |
|------|------|------|
| 1 | **실제 매매 로직 검증** | 봇 시작 시 엔진 기동·업비트 API 연동 검증. 푸시/차트보다 선행 권장. |
| 2 | **푸시 알림 (텔레그램)** | 매매·손절·긴급정지 시 알림. 텔레그램 1차, FCM은 2차. |
| 3 | **일별 수익 시계열 API** | 백엔드 PnL 이력 API + Flutter 차트 확장. |

---

## 5. 123(화이트보드) 작업 지시 초안 (복사·수정용)

아래를 123(화이트보드) 「작업 지시」에 넣을 때 개발관이 순서대로 수행할 수 있도록 번호를 부여했습니다. 필요 시 기획관이 일부만 발췌하거나 기간을 나눠 지시할 수 있습니다.

```
[기획 2차 — 실제 매매 검증 · 푸시 알림 · 일별 PnL]

1. 실제 매매 로직 검증
   - 백엔드: POST /api/v1/bot/start 시 트레이딩 엔진 기동(또는 최소 검증용 업비트 API 호출). asyncio 백그라운드 태스크 또는 동일 프로세스 내 루프. upbit-trading-system의 trading 모듈 참고·이식 검토.
   - 봇 정지 시 해당 태스크/루프 종료, 미체결 주문 취소.
   - 검증 모드 또는 소액 테스트 시나리오 문서화(실제 매매는 사용자 책임 안내).
   - 검증관: 봇 시작 후 로그/상태에서 업비트 API 호출 이력 확인, 정지 시 정상 종료 확인.

2. 푸시 알림 (텔레그램 1차)
   - 백엔드: 텔레그램 발송 모듈 추가(또는 TelegramNotifier 이식). TELEGRAM_BOT_TOKEN 환경변수, 사용자별 user.telegram_chat_id 사용.
   - 발송 시점: 매수 체결·매도 체결·손절·긴급 정지 시 해당 user의 telegram_chat_id로 발송. chat_id 없으면 건너뜀.
   - 메시지: 코인·가격·금액·손익 등 최소 정보 포함. 상세 기획: docs/기획_매매검증_푸시_일별PnL.md 2장.
   - 검증관: 토큰·채팅 ID 설정 후 테스트 발송, 미설정 시 건너뜀 확인.

3. 일별 수익 시계열 API 및 차트
   - 백엔드: GET /api/v1/bot/pnl-history?days=30 추가. Trade 테이블 일별 realized_pnl 집계, [{ date, pnl, (선택) pnl_krw }] 반환.
   - Flutter: api_service에 getPnlHistory(days), 대시보드에서 일별 PnL 라인/막대 차트 표시. One UI·기존 카드 스타일 유지.
   - 상세 기획: docs/기획_매매검증_푸시_일별PnL.md 3장.
   - 검증관: API 응답 형식·Flutter 차트 반영·거래 없음 날 처리 확인.
```

---

**문서 끝.** 개발관·검증관은 본 문서와 PRD(docs/PRD_업비트_자동매매_앱.md), UI_UX_가이드_적용.md를 함께 참고하면 됩니다.
