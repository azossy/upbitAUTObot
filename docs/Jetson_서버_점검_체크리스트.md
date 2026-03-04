# Jetson 서버 점검 체크리스트

**목적**: PC가 아닌 **실제 Jetson 서버**에서 설정·코드·API·메일까지 **전반적으로 준비가 완료되었는지** 확인한다.  
**접속**: SSH `ssh upbit@100.80.178.45` (접속 정보는 팀 내에서만 안전하게 공유. **채팅·문서에 비밀번호 입력 금지.**)

---

## 0. 설정 파일 및 전반 준비 체크 (Jetson에서 확인)

### 0.1 설정 파일 위치·존재

```bash
ls -la /home/upbit/upbitAUTObot/backend/.env
```

- **확인**: `.env` 파일이 있어야 함. 없으면 `cp .env.example .env` 후 편집.

### 0.2 .env 필수 항목 (반드시 설정)

| 변수 | 설명 | 확인 방법 (값이 비어 있으면 안 됨) |
|------|------|-------------------------------------|
| `JWT_SECRET_KEY` | 64자 hex. 기본값이면 기동은 되나 보안 취약 | `grep JWT_SECRET_KEY .env` — `CHANGE_ME` 아니어야 함 |
| `ENCRYPTION_KEY` | 64자 hex. API 키 암호화 | `grep ENCRYPTION_KEY .env` — `0`*64 아니어야 함 |

- 생성 예: `python3 -c "import secrets; print(secrets.token_hex(32))"` (두 번 실행해 각각 넣기)

### 0.3 .env 선택·기능별 항목

| 기능 | 변수 | 비고 |
|------|------|------|
| **회원가입 이메일 인증** | `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` | 비어 있으면 인증 메일 503. `SMTP_PORT`, `EMAIL_FROM`, `VERIFICATION_CODE_EXPIRE_MINUTES` 권장 |
| **텔레그램 알림** | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_DEFAULT_CHAT_ID` | 선택 |
| **구글/카카오 로그인** | `GOOGLE_CLIENT_ID`, `KAKAO_REST_API_KEY` | 선택 |
| **FCM 푸시** | `GOOGLE_APPLICATION_CREDENTIALS` | JSON 경로. 선택 |
| **CORS** | `CORS_ORIGINS` | 기본값으로도 동작. 디버그 시 `DEBUG=true` 가능 |

### 0.4 코드 버전 (최신 여부) — 갱신 방법

**PC에서 한 번에 실행 (비밀번호 입력 필요)**  
- PowerShell: `.\scripts\jetson_update_and_restart.ps1` (프로젝트 루트에서). SSH 비밀번호 → sudo 비밀번호 입력.  
- 또는 수동: `ssh upbit@100.80.178.45` 로그인 후 아래 실행.

```bash
cd ~/upbitAUTObot && git pull && sudo systemctl restart upbit-backend
```

- **확인**: 인증 메일·회원가입 플로우가 포함된 **최신 백엔드**인지.  
  라우트 존재 확인: `grep -l "send-verification-email" backend/app/routers/auth.py` → 파일에서 해당 문자열이 있어야 함.

### 0.5 systemd 서비스 설정

```bash
cat /etc/systemd/system/upbit-backend.service
```

- **확인**: `WorkingDirectory`, `EnvironmentFile`, `ExecStart` 경로가 실제 Jetson 경로와 일치하는지 (`/home/upbit/upbitAUTObot/backend` 등).

### 0.6 DB 파일 (SQLite)

```bash
ls -la /home/upbit/upbitAUTObot/backend/*.db 2>/dev/null || echo "DB 없음(첫 기동 시 생성됨)"
```

- **확인**: 기동 후 `upbit_trading.db` 등이 생성되어 있으면 정상.

---

## 1. Jetson에 SSH 접속 후 실행할 명령 (순서대로)

### 1.1 백엔드 서비스 상태

```bash
sudo systemctl status upbit-backend
```

- **확인**: `active (running)` 이어야 함. 실패 시 아래 1.4 로그 확인.

### 1.2 로컬에서 health 확인 (Jetson 자신이 8000 포트 응답하는지)

```bash
curl -s http://127.0.0.1:8000/health
```

- **기대**: `{"status":"ok","version":"1.1.0"}`

### 1.3 인증 메일 발송 API (회원가입 시 호출되는 엔드포인트)

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/send-verification-email \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'
```

- **가능한 결과**:
  - `{"message":"인증 메일을 발송했습니다. ..."}` → 정상
  - `503` + "이메일 발송이 설정되지 않았습니다" → SMTP 미설정
  - `400` + "이미 등록된 이메일입니다" → 해당 이메일 이미 가입됨 (서버·경로는 정상)
  - `404` → 라우트/프록시 문제 가능

### 1.4 최근 로그 (에러 있을 때)

```bash
sudo journalctl -u upbit-backend -n 50 --no-pager
```

- ValidationError, ModuleNotFoundError, SMTP 오류 등 확인.

### 1.5 메일 설정 테스트 (baejjangi CLI)

```bash
cd ~/upbitAUTObot/backend
source venv/bin/activate
python baejjangi.py test mail
# 또는 빌드된 실행 파일: ./dist/baejjangi test mail
```

- **기대**: "성공: ... 로 테스트 메일을 발송했습니다."

### 1.6 Tailscale 상태 (Jetson이 같은 네트워크에 있는지)

```bash
tailscale status
```

- **확인**: up 상태, 100.x.x.x IP 부여됐는지.

### 1.7 API 경로 노출 여부 (최신 코드 반영 확인)

```bash
curl -s http://127.0.0.1:8000/openapi.json | grep -o '"/[^"]*"' | sort -u
```

- **확인**: 목록에 `/api/v1/auth/send-verification-email`, `/api/v1/auth/verify-and-register` 가 있어야 회원가입 인증 플로우 사용 가능. 없으면 백엔드가 구버전이므로 `git pull` 후 재시작.

---

## 2. 점검 결과 정리

| 항목 | 결과 (예: OK / 실패·메시지) |
|------|-----------------------------|
| .env 존재 | |
| JWT_SECRET_KEY / ENCRYPTION_KEY 변경 여부 | |
| SMTP 설정 (회원가입 인증용) | |
| 코드 최신 (send-verification-email 포함) | |
| systemd upbit-backend | |
| curl 127.0.0.1:8000/health | |
| POST send-verification-email | |
| openapi에 인증 메일 경로 노출 | |
| journalctl 최근 에러 | |
| baejjangi test mail | |
| tailscale status | |

---

## 3. 접속 정보 보안

- **Jetson SSH 아이디/비밀번호**는 팀만 알면 되며, **채팅·공개 문서에 적지 않는다.**
- 필요 시 비밀번호 관리자·암호화된 메모 등으로 팀 내에서만 공유.

---

## 4. 전반 준비 완료 기준 (한눈에)

서버에 **모든 게 준비된 상태**는 아래가 모두 충족될 때입니다.

- **설정**: `.env` 존재, `JWT_SECRET_KEY`·`ENCRYPTION_KEY` 실제 값으로 변경됨.
- **회원가입 인증**: `SMTP_HOST`·`SMTP_USER`·`SMTP_PASSWORD` 설정됨. `baejjangi test mail` 성공.
- **코드**: 최신 배포본으로 `send-verification-email`, `verify-and-register` 라우트가 노출됨 (`openapi.json` 또는 1.3·1.7 확인).
- **프로세스**: `systemctl status upbit-backend` → `active (running)`.
- **API**: `curl 127.0.0.1:8000/health` → 200, `POST send-verification-email` → 200 또는 503(SMTP 미설정 시).
- **네트워크**: `tailscale status` → up, 100.x.x.x 부여.
