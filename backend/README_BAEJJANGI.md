# baejjangi CLI

배짱이 v1.4 운영용 CLI. 설정 변경 및 메일/텔레그램/카카오 테스트.

## 사용법

- **인자 없이 실행** → 사용법 안내
  ```bash
  python baejjangi.py
  # 또는 컴파일 후: ./baejjangi  /  baejjangi.exe
  ```
- **설정**: `baejjangi set telegram` / `baejjangi set email`
- **테스트**: `baejjangi test mail` / `baejjangi test telegram` / `baejjangi test kakao`

## 테스트 명령 (Jetson 등 서버에서 동작 확인)

| 명령 | 설명 |
|------|------|
| `baejjangi test mail` | .env의 SMTP로 테스트 메일 1통 발송. 수신 주소 입력 프롬프트 |
| `baejjangi test telegram` | .env의 봇 토큰·Chat ID로 테스트 메시지 1통 발송 |
| `baejjangi test kakao` | KAKAO_REST_API_KEY 설정 여부 확인 |

## 단일 실행 파일로 빌드 (PyInstaller)

Jetson/서버에서 `python` 없이 `./baejjangi` 만으로 실행하려면:

```bash
cd backend
pip install pyinstaller
python build_baejjangi.py
```

결과: `dist/baejjangi` (Linux/Jetson) 또는 `dist/baejjangi.exe` (Windows).  
이 파일을 PATH에 두거나 프로젝트 루트에 복사 후 실행. **실행 시 .env는 현재 작업 디렉터리(cwd)의 backend/.env 를 사용**하므로, 서버에서는 `backend` 디렉터리에서 실행하거나 `--env-file /path/to/.env` 로 지정.

## 리눅스에서 단일 실행 파일 빌드

리눅스(Jetson 등)에서 `./baejjangi` 한 파일만으로 실행하려면 같은 서버에서 PyInstaller로 빌드하면 됩니다.

1. **환경**: Python 3.10+ 가 설치된 리눅스, 프로젝트 `backend` 디렉터리 존재.
2. **빌드**:
   ```bash
   cd backend
   pip install -r requirements.txt   # 필요 시
   pip install pyinstaller
   python build_baejjangi.py
   ```
3. **결과**: `backend/dist/baejjangi` 실행 파일이 생성됩니다.
4. **실행**: `./dist/baejjangi` 또는 PATH에 `dist`를 넣은 뒤 `baejjangi --help` 등으로 사용.  
   서비스(baejjangi-backend) 제어는 리눅스에서만: `baejjangi --stop`, `baejjangi --restart`, `baejjangi --status`.

## 서비스 제어 옵션 (리눅스 전용)

| 옵션 | 설명 |
|------|------|
| `baejjangi --stop` | systemd 서비스 `baejjangi-backend` 중지 |
| `baejjangi --restart` | systemd 서비스 `baejjangi-backend` 재시작 |
| `baejjangi --status` | systemd 서비스 `baejjangi-backend` 상태 출력 |
| `baejjangi --update` | GitHub에서 최신 코드 pull, pip 설치, 서비스 재시작, health 검사 (**환경설정 .env 는 변경하지 않음**) |
| `baejjangi --reinstall` | **클린 재설치**: 기존 설치 제거 후 저장소 클론·설정(.env/DB) 복원·venv·서비스 기동·서버 테스트(health/인증메일/로그인 API) 후 결과를 표로 출력 |

위 옵션은 **리눅스**에서만 동작하며, Windows에서는 "리눅스에서만 지원됩니다" 메시지가 나옵니다.

### --update 상세

- 현재 프로젝트가 Git 저장소인지 확인 후 `git pull` 실행.
- `backend/venv` 또는 시스템 `pip3`로 `pip install -r requirements.txt` 실행.
- `systemctl restart baejjangi-backend` 후 `/health` 호출로 정상 기동 여부 확인.
- 출력: 이전 버전 → 현재 버전, health 결과.

### --reinstall 상세

- **백업**: `backend/.env`, `backend/*.db` 를 임시 디렉터리로 복사.
- **중지**: `baejjangi-backend` (및 구 서비스명 `upbit-backend`) 중지.
- **클론**: 상위 디렉터리에 `baejjangi_new` 로 저장소 클론.
- **복원**: 백업한 `.env`, `*.db` 를 `baejjangi_new/backend/` 에 복원.
- **설치**: `baejjangi_new/backend` 에 venv 생성 및 `pip install -r requirements.txt`.
- **systemd**: 기존 `upbit-backend.service` 가 있으면 `baejjangi-backend.service` 로 변경, 경로를 `baejjangi/backend` 로 통일.
- **교체**: 기존 `baejjangi` 폴더를 `baejjangi_old` 로 이동 후, `baejjangi_new` 를 `baejjangi` 로 이동.
- **기동**: `systemctl start baejjangi-backend` 후 서버 테스트(health, 인증메일 API, 로그인 API) 실행.
- **출력**: 재설치 결과 표(health/인증메일/로그인 API 상태, 백엔드 버전).

## 사용자 목록 (--user)

| 옵션 | 설명 |
|------|------|
| `baejjangi --user` | 앱 사용자 목록 + 최근 접속일(last_login_at)을 DB에서 조회해 표로 출력. `.env`의 DATABASE_URL 사용. |
