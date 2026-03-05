# API 명세서 — 배짱이 v1.0

**저작자**: 차리 (challychoi@me.com)

**문서 버전**: v1.0  
**작성일**: 2026-03-02  
**참조**: [업비트 API 개요](https://docs.upbit.com/kr/reference/api-overview)

---

## 1. 개요

### 1.1 Base URL
```
http://{서버주소}:8000
```

### 1.2 인증
- **Access Token**: `Authorization: Bearer {access_token}`
- **Refresh Token**: HttpOnly Cookie (선택)

### 1.3 공통 응답 형식
```json
{
  "success": true,
  "data": { ... },
  "message": "성공"
}
```

---

## 2. 인증 API (`/api/v1/auth`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | /register | 회원가입 |
| POST | /login | 로그인 |
| POST | /refresh | Access Token 갱신 |
| POST | /google | 구글 로그인 (id_token). 미가입 시 need_register+email/name 반환 |
| POST | /kakao | 카카오 로그인 (access_token). 미가입 시 need_register+email/name 반환 |
| POST | /complete-google-register | 구글 OAuth 회원가입 완료 (id_token, nickname) |
| POST | /complete-kakao-register | 카카오 OAuth 회원가입 완료 (access_token, nickname) |
| POST | /logout | 로그아웃 |
| GET | /me | 내 정보 조회 |
| PUT | /me | 프로필 수정 |
| PUT | /password | 비밀번호 변경 |

### POST /register
**Request**
```json
{
  "email": "user@example.com",
  "password": "password123!",
  "nickname": "닉네임"
}
```

### POST /login
**Request**
```json
{
  "email": "user@example.com",
  "password": "password123!"
}
```
**Response**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "nickname": "닉네임",
    "role": "USER"
  }
}
```

---

## 3. 봇 API (`/api/v1/bot`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | /status | 봇 상태 조회 |
| POST | /start | 봇 시작 |
| POST | /stop | 봇 정지 |
| PUT | /config | 봇 설정 변경 |
| GET | /positions | 보유 포지션 조회 |
| GET | /trades | 거래 내역 조회 |
| GET | /trades/summary | 거래 성과 요약 |
| POST | /api-keys | API 키 등록 |
| GET | /api-keys | API 키 목록 |
| DELETE | /api-keys/{id} | API 키 삭제 |

### GET /status
**Response**
```json
{
  "status": "RUNNING",
  "market_mode": "BULL",
  "market_score": 65,
  "total_pnl": 125000,
  "win_rate": 0.58,
  "daily_pnl": 15000,
  "weekly_pnl": 45000
}
```

### PUT /config
**Request**
```json
{
  "max_investment_ratio": 0.5,
  "max_positions": 7,
  "stop_loss_pct": 2.5,
  "take_profit_pct": 7.0,
  "telegram_chat_id": "123456789"
}
```

### POST /api-keys
**Request**
```json
{
  "access_key": "업비트_Access_Key",
  "secret_key": "업비트_Secret_Key",
  "label": "메인계정"
}
```

---

## 4. 업비트 API 연동 (서버 내부)

서버는 [업비트 API](https://docs.upbit.com/kr/reference/api-overview)와 직접 연동합니다.

### 4.1 Quotation API (인증 불필요)
| 용도 | REST | WebSocket |
|------|------|-----------|
| 캔들 | GET /v1/candles/{interval} | O |
| 현재가 | GET /v1/ticker | O |
| 호가 | GET /v1/orderbook | O |
| 체결 | GET /v1/trades/ticks | O |

### 4.2 Exchange API (JWT 인증 필수)
| 용도 | REST |
|------|------|
| 잔고 | GET /v1/accounts |
| 주문 생성 | POST /v1/orders |
| 주문 취소 | DELETE /v1/order |
| 주문 조회 | GET /v1/order, GET /v1/orders |

### 4.3 Rate Limit
- **초당 10회** 제한
- 요청 간 최소 0.1초 간격 권장
