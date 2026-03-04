# 배짱이 v1.1 — Jetson Orin Nano + Tailscale 서버 세팅

**저작자**: 차리 (challychoi@me.com)

Jetson Orin Nano Super 8GB (Ubuntu)에 백엔드를 설치하고, **Tailscale**로 포트포워딩 없이 현재 PC·스마트폰에서 접속하는 방법입니다.

**※ 본인 Jetson Tailscale IP**: `100.80.178.45`  
- SSH: `ssh upbit@100.80.178.45`  
- 앱 API 서버 주소: `http://100.80.178.45:8000`

---

## 1. 전체 흐름 요약

1. **Jetson**에 Tailscale 설치 → Jetson 전용 Tailscale IP(100.x.x.x) 부여
2. **현재 PC**에 Tailscale 설치 → 같은 계정이면 자동으로 Jetson과 같은 네트워크
3. PC에서 **SSH**로 Jetson 접속: `ssh 사용자명@Jetson의TailscaleIP`
4. Jetson에 **배짱이 백엔드** 설치 후 systemd로 상시 실행
5. Flutter 앱 **API 서버 주소**를 `http://Jetson의TailscaleIP:8000` 으로 설정

**장점**: 공유기 포트포워딩 불필요, 외부에서도 Tailscale만 깔면 같은 네트워크처럼 접속 가능.

---

## 2. 1단계: Jetson에 Tailscale 설치 (Jetson에서 실행)

Jetson에 모니터·키보드로 직접 접속했거나, **같은 공유기/유선**으로 잠깐 연결해 SSH 가능한 상태에서 진행합니다.

### 2.1 Ubuntu에서 Tailscale 설치

```bash
# 공식 스크립트 (권장)
curl -fsSL https://tailscale.com/install.sh | sh

# 설치 후 서비스 기동 및 로그인
sudo tailscale up
```

브라우저가 열리거나 터미널에 URL이 뜨면, 그 주소로 들어가서 **Tailscale 계정으로 로그인**합니다. (계정 없으면 tailscale.com에서 무료 가입)

### 2.2 Jetson의 Tailscale IP 확인

```bash
tailscale ip -4
```

예: `100.101.102.103` 같은 **100.x.x.x** 주소가 나오면 이게 Jetson의 Tailscale IP입니다.  
이후 PC·폰에서 Jetson에 접속할 때 이 주소를 사용합니다.

---

## 3. 2단계: 현재 PC(Windows)에 Tailscale 설치

1. https://tailscale.com/download 에서 **Windows**용 설치
2. 설치 후 로그인 → **Jetson과 같은 Tailscale 계정** 사용
3. 로그인되면 PC에도 Tailscale IP(100.x.x.x)가 부여됨

이제 두 기기가 **Tailscale 네트워크**로 연결된 상태입니다.

### 3.1 PC에서 Jetson으로 SSH 접속

PowerShell 또는 CMD에서:

```powershell
ssh 사용자명@Jetson의TailscaleIP
```

예: Jetson SSH 사용자명 `upbit`, Tailscale IP `100.80.178.45`:

```powershell
ssh upbit@100.80.178.45
```

처음 접속 시 fingerprint 확인 메시지에서 `yes` 입력.  
비밀번호는 Jetson Ubuntu 사용자 비밀번호입니다.

---

## 4. 3단계: Jetson에 배짱이 백엔드 설치

아래는 **Jetson에 SSH로 접속한 뒤** 실행하는 명령입니다.

### 4.1 필수 패키지

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
```

Python 3.10 이상이어야 합니다. 확인:

```bash
python3 --version
```

### 4.2 프로젝트 복사 (둘 중 하나)

**방법 A — Git으로 클론 (PC에서 이미 GitHub에 올려둔 경우)**

```bash
cd ~
git clone https://github.com/azossy/upbitAUTObot.git
cd upbitAUTObot
```

**방법 B — PC에서 SCP로 복사 (현재 작업 폴더에서)**

PC PowerShell에서 (Tailscale로 연결된 상태에서):

```powershell
scp -r "C:\Users\chall\Desktop\파이썬공부방\업비트 자동매매\backend" upbit@100.80.178.45:~/
scp "C:\Users\chall\Desktop\파이썬공부방\업비트 자동매매\backend\.env.example" upbit@100.80.178.45:~/backend/
```

Jetson에서는:

```bash
cd ~
mkdir -p upbitAUTObot
mv backend upbitAUTObot/
cd upbitAUTObot/backend
```

### 4.3 가상환경 + 의존성 설치

```bash
cd ~/upbitAUTObot/backend
# 또는 clone 한 경우: cd ~/upbitAUTObot/backend

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4.4 .env 설정

```bash
cp .env.example .env
nano .env
```

다음 항목을 **반드시** 수정합니다.

| 변수 | 설정 값 |
|------|---------|
| **JWT_SECRET_KEY** | `python3 -c "import secrets; print(secrets.token_hex(32))"` 로 생성한 64자 hex |
| **ENCRYPTION_KEY** | 위와 동일한 방식으로 새로 생성한 64자 hex |
| **DEBUG** | `false` |
| **CORS_ORIGINS** | `*` (Tailscale IP만 쓸 거면 `http://100.x.x.x` 형태로 여러 개 comma 구분도 가능) |

저장: `Ctrl+O` → Enter → `Ctrl+X`

### 4.5 수동 실행 테스트

```bash
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

**PC 브라우저**에서 `http://Jetson의TailscaleIP:8000/health` 접속해 보세요.  
`{"status":"ok","version":"1.0.0"}` 이 나오면 정상입니다.  
테스트 후 서버는 `Ctrl+C`로 종료합니다.

### 4.6 systemd로 상시 실행

```bash
sudo nano /etc/systemd/system/upbit-backend.service
```

아래 내용 붙여넣고, 경로가 다르면 수정합니다. (사용자명 `upbit`, 경로 `/home/upbit/upbitAUTObot/backend`)

```ini
[Unit]
Description=배짱이 v1.1 Backend API
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=upbit
WorkingDirectory=/home/upbit/upbitAUTObot/backend
EnvironmentFile=/home/upbit/upbitAUTObot/backend/.env
ExecStart=/home/upbit/upbitAUTObot/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

저장 후:

```bash
sudo systemctl daemon-reload
sudo systemctl enable upbit-backend
sudo systemctl start upbit-backend
sudo systemctl status upbit-backend
```

`active (running)` 이면 성공입니다.

---

## 5. 4단계: Flutter 앱에서 서버 주소 설정

스마트폰·PC의 배짱이 앱에서:

1. **설정** → **API 서버 주소** 입력란에  
   `http://Jetson의TailscaleIP:8000`  
   예: `http://100.101.102.103:8000`
2. **저장** 후 대시보드 등에서 API가 잘 호출되는지 확인

스마트폰에서 접속하려면 **폰에도 Tailscale 앱**을 설치하고 같은 계정으로 로그인해야 합니다. 그러면 폰에서도 Jetson의 100.x.x.x 주소로 접근 가능합니다.

---

## 6. 정리 체크리스트

- [ ] Jetson에 Tailscale 설치 및 `tailscale up` 로그인
- [ ] Jetson Tailscale IP 확인 (`tailscale ip -4`)
- [ ] PC에 Tailscale 설치, 같은 계정 로그인
- [ ] PC에서 `ssh 사용자@Jetson_Tailscale_IP` 로 접속 확인
- [ ] Jetson에 backend 설치 (venv, requirements, .env)
- [ ] .env 에 JWT_SECRET_KEY, ENCRYPTION_KEY, DEBUG=false 설정
- [ ] `http://Jetson_IP:8000/health` 로 응답 확인
- [ ] systemd 서비스 등록 및 enable/start
- [ ] Flutter 앱 API 서버 주소를 `http://Jetson_Tailscale_IP:8000` 로 설정
- [ ] (스마트폰 사용 시) 폰에 Tailscale 앱 설치·동일 계정 로그인

---

## 7. 참고

- **방화벽**: Tailscale은 사용자 공간 VPN이라 보통 **라우터 포트포워딩이 필요 없습니다**. Jetson 방화벽(ufw)에서 8000 포트를 열 필요는 없고, `0.0.0.0:8000`으로 띄우면 Tailscale 인터페이스에서 접근 가능합니다.
- **재부팅**: systemd에 등록했으므로 Jetson 재부팅 후에도 백엔드가 자동으로 올라옵니다. Tailscale도 부팅 시 자동 기동됩니다.
- **문제 발생 시**: `sudo journalctl -u upbit-backend -f` 로 로그 확인.

추가: docs/배포_가이드.md (환경변수·CORS·점검 체크리스트)
