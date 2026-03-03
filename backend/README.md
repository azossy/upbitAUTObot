# 배짱이 v1.0 — 백엔드

**저작자**: 차리 (challychoi@me.com)

Python FastAPI + SQLite 기반 백엔드 서버.

## 실행 방법

```bash
# 1. 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate   # Windows

# 2. 의존성 설치
pip install -r requirements.txt

# 3. .env 설정
copy .env.example .env
# JWT_SECRET_KEY, ENCRYPTION_KEY 수정 (필수)

# 4. 서버 실행
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Flutter 웹(Chrome)에서 로그인이 안 될 때

- 앱에서 **"서버에 연결할 수 없습니다"** → 백엔드를 먼저 실행했는지 확인 (위 4번).
- **CORS 오류**로 로그인 실패 시: `.env`에 `DEBUG=true` 로 설정하면 모든 출처 허용됩니다. (개발용)
- 브라우저에서 http://localhost:8000/health 접속해 `{"status":"ok"}` 가 보이면 백엔드는 정상입니다.

## API 문서

- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health

## 주요 엔드포인트

| 경로 | 설명 |
|------|------|
| POST /api/v1/auth/register | 회원가입 |
| POST /api/v1/auth/login | 로그인 |
| GET /api/v1/auth/me | 내 정보 |
| GET /api/v1/bot/status | 봇 상태 |
| POST /api/v1/bot/start | 봇 시작 |
| POST /api/v1/bot/stop | 봇 정지 |
| POST /api/v1/bot/api-keys | API 키 등록 |
