# baejjangi CLI

배짱이 v1.1 운영용 CLI. 설정 변경 및 메일/텔레그램/카카오 테스트.

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
