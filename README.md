# 배짱이 (Baejjangi) — 업비트 현물 자동매매

**저작자**: 차리 (challychoi@me.com)

업비트 거래소 **현물** 자동매매를 스마트폰 앱으로 제어·모니터링하는 시스템입니다.  
서버(Jetson Orin Nano, PC 등)에서 24시간 봇을 돌리고, Android 앱으로 시작/정지·설정·잔고·포지션·푸시 알림을 받을 수 있습니다.

---

## 🚀 빠른 실행 방법 (친절 안내)

처음이셔도 아래 순서대로만 하시면 됩니다.

### 1단계: Android 앱 받기

1. **[Releases](https://github.com/azossy/upbitAUTObot/releases)** 페이지로 갑니다.
2. 가장 위에 있는 **최신 버전**(예: v1.0.0)을 클릭합니다.
3. **Assets** 안에 있는 **app-release.apk** 를 눌러 다운로드합니다.
4. 다운로드한 APK 파일을 **휴대폰으로 옮깁니다.** (USB, 클라우드, 메신저 등 편한 방법으로)
5. 휴대폰에서 APK 파일을 탭해 **설치**합니다.  
   - "알 수 없는 앱 설치" 허용이 뜨면 **허용**을 선택해 주세요.
6. 설치가 끝나면 **배짱이** 앱 아이콘이 생깁니다. 실행해 보세요.

### 2단계: 서버 준비 (본인 서버가 있어야 앱이 연결됩니다)

서버는 **한 번만** 설치해 두면 됩니다. Jetson, Ubuntu PC, 또는 Windows PC에서 돌리면 됩니다.

**가장 짧은 방법 (Ubuntu/Jetson):**

```bash
git clone https://github.com/azossy/upbitAUTObot.git
cd upbitAUTObot/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

그다음 **.env** 파일을 열어서 아래 두 값을 **꼭** 바꿔 주세요.

- **JWT_SECRET_KEY**, **ENCRYPTION_KEY**: 터미널에서  
  `python3 -c "import secrets; print(secrets.token_hex(32))"`  
  를 두 번 실행해서 나온 64자리 문자열을 각각 복사해 넣습니다.

저장한 뒤 서버를 띄웁니다.

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

"Application startup complete" 가 보이면 서버가 켜진 겁니다.  
(같은 공유기라면 PC/폰 브라우저에서 `http://서버IP:8000/health` 로 접속해 `{"status":"ok"}` 가 나오는지 확인해 보세요.)

**Jetson + Tailscale**로 하시려면 [docs/서버_설치_Jetson_Tailscale.md](docs/서버_설치_Jetson_Tailscale.md) 를 보시면 단계별로 잘 나와 있습니다.

### 3단계: 앱에서 서버 연결

1. 휴대폰에서 **배짱이** 앱을 엽니다.
2. **설정**(톱니바퀴) 메뉴로 들어갑니다.
3. **API 서버 주소** 칸에 서버 주소를 입력합니다.  
   - 예: `http://192.168.0.10:8000` (같은 공유기일 때 서버 IP)  
   - 예: `http://100.101.102.103:8000` (Tailscale 사용 시 Jetson의 Tailscale IP)
4. **저장**을 누릅니다.

이제 앱이 그 서버와 통신합니다.

### 4단계: 로그인하고 쓰기

1. **회원가입** 또는 **로그인**(이메일·구글·카카오 중 편한 것)을 합니다.
2. **설정**에서 **업비트 API 키**를 등록합니다. (업비트 마이페이지에서 발급한 Access Key, Secret Key)
3. **매매 설정**(투자 비율, 손절 %, 익절 %)을 원하는 대로 넣습니다.
4. **대시보드**에서 **봇 시작**을 누르면, 서버에서 봇이 돌기 시작합니다.  
   잔고·포지션·거래 내역은 대시보드와 메뉴에서 확인하실 수 있습니다.

여기까지 하시면 **빠른 실행**은 완료입니다.  
상세 서버 설치·환경변수·상시 실행(systemd)은 [docs/배포_가이드.md](docs/배포_가이드.md) 를 참고하세요.

---

## 📖 프로젝트 설명

### 이게 뭔가요?

- **업비트** 거래소 API와 연동해, 지정한 설정(투자 비율, 손절/익절 %)에 따라 **현물** 자동매매를 도와주는 봇입니다.
- 봇은 **서버**에서 돌고, **Android 앱(배짱이)** 으로 시작/정지, API 키·매매 설정, 잔고·포지션·거래 내역을 확인합니다.
- 매수/매도/손절/긴급 정지 시 **푸시 알림**(FCM·텔레그램)을 받을 수 있습니다.

### 기술 구성

| 구분 | 내용 |
|------|------|
| **앱** | Flutter (Android). 로그인(이메일·구글·카카오), 생체인증, 대시보드, 포지션, 거래내역, 설정 |
| **서버** | Python FastAPI. 인증(JWT), 업비트 API 연동, 봇 제어, SQLite DB |
| **푸시** | FCM + 텔레그램 (선택) |

### 사용 흐름

1. 서버를 한 번 설치·실행해 두고 (본인 PC, Jetson 등)
2. Android 앱에서 회원가입/로그인 후 **API 서버 주소**를 그 서버로 설정
3. **업비트 API 키**를 앱에서 등록 (서버에 암호화 저장)
4. **매매 설정**(투자 비율, 손절 %, 익절 %) 입력 후 **봇 시작**
5. 대시보드에서 잔고·포지션·수익률 확인, 필요 시 봇 정지

※ 자동매매로 인한 손실은 사용자 책임이며, 서비스는 투자 결과에 대해 책임지지 않습니다.

---

## 📐 현물 거래 진입·매각 로직 (트레이딩 기법)

배짱이는 **업비트 현물만** 대상으로 하며, 숏(공매도)은 사용하지 않습니다.  
**언제 매수하고, 언제 매도하는지**를 **2~3단계 확인**으로 판단해, 한 번의 신호로 덜컥 주문하는 일을 줄이도록 설계되어 있습니다.

**진입(매수)**: 1차 시장 국면 → 2차 코인별 추세(EMA 골든크로스, 4시간봉 정배열, ADX 25 이상, 거래량) → 3차 진입 타이밍(눌림목 또는 강한 추세). **세 단계 모두 통과 시에만** 매수합니다.

**매각(매도)**: 1순위 국면 하락 전환(2단계 확인) → 2순위 손절 %(2단계 확인) → 3순위 데드크로스(2단계 확인) → 4~6순위 분할 익절(+5%/+10%/+15%, 2단계 확인) → 7순위 시간 손절(3단계 확인). 우선순위가 높은 **한 가지** 사유로만 청산합니다.

**지표**: EMA, ADX, 거래량, RSI, 시장 점수를 사용합니다.

👉 **아주 자세한 설명**(왜 다중 확인을 쓰는지, 단계별 조건, 예시 시나리오, FAQ)은 **[docs/트레이딩_로직_상세_가이드.md](docs/트레이딩_로직_상세_가이드.md)** 에 길게 친절하게 적어 두었습니다. 처음 보시는 분도 차근차근 읽을 수 있습니다.

※ v1.0 서버는 **검증 모드**(잔고 조회·API 연동 확인)까지 구현되어 있으며, 위 전략에 따른 실제 주문 로직은 추후 버전에서 적용될 예정입니다.

---

## 🔧 자세한 설치 방법

### 요구사항

- **서버**: Python 3.10+, Ubuntu(권장) 또는 Windows. (Jetson Orin Nano 등에서도 동작)
- **앱**: Android 5.0 이상. (APK는 Releases에서 받거나, 아래처럼 직접 빌드)

### 1. 저장소 클론

```bash
git clone https://github.com/azossy/upbitAUTObot.git
cd upbitAUTObot
```

### 2. 서버(백엔드) 설치 및 실행

```bash
cd backend
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` 파일을 열어 다음을 **반드시** 수정합니다.

- **JWT_SECRET_KEY**, **ENCRYPTION_KEY**: 아래로 64자 hex 생성 후 입력  
  `python3 -c "import secrets; print(secrets.token_hex(32))"`
- **DEBUG**: 운영 시 `false`
- **CORS_ORIGINS**: Flutter 앱에서 접속하는 주소 (테스트 시 `*` 가능)

저장 후 서버 실행:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

브라우저에서 `http://서버IP:8000/health` 로 `{"status":"ok","version":"1.0.0"}` 이 나오면 정상입니다.  
상시 실행은 [docs/배포_가이드.md](docs/배포_가이드.md) 의 systemd 예시를 참고하세요.

### 3. Android 앱 — APK 받기 또는 직접 빌드

**방법 A: 이미 빌드된 APK 사용 (권장)**  
- [Releases](https://github.com/azossy/upbitAUTObot/releases) 에서 `app-release.apk` 다운로드 후 Android 기기에 설치.

**방법 B: 직접 빌드 후 GitHub Release에 올리기**

APK를 직접 컴파일해서 GitHub에 올리려면:

1. **Flutter**와 **Android SDK**가 설치된 PC에서 프로젝트 루트로 이동합니다.
2. **Windows**: `upbit_trading_app\build_apk.bat` 더블클릭 또는 터미널에서 실행.  
   **Mac/Linux**: `cd upbit_trading_app && flutter pub get && flutter build apk --release`
3. 빌드가 끝나면 `upbit_trading_app/build/app/outputs/flutter-apk/app-release.apk` 가 생성됩니다.
4. 이 APK를 **GitHub Release**에 올리려면 (GitHub CLI 설치 후):  
   `gh release upload v1.0.0 upbit_trading_app/build/app/outputs/flutter-apk/app-release.apk --repo azossy/upbitAUTObot --clobber`  
   (버전 태그 `v1.0.0`은 이미 만든 Release가 있어야 합니다. 새 버전이면 먼저 `gh release create v1.0.1 --title "배짱이 v1.0.1"` 로 생성한 뒤 upload 하세요.)

자세한 절차는 [docs/APK_빌드_및_배포.md](docs/APK_빌드_및_배포.md) 를 참고하세요.

### 4. 앱에서 서버 연결

- 앱 실행 → **설정** → **API 서버 주소**에 서버 주소 입력 (예: `http://192.168.0.10:8000` 또는 Tailscale IP `http://100.x.x.x:8000`)
- 저장 후 로그인/회원가입하여 사용합니다.

---

## 📁 프로젝트 구조

```
upbitAUTObot/
├── backend/              # FastAPI 서버 (Python)
│   ├── app/
│   │   ├── routers/      # API 라우트 (auth, bot, market, news)
│   │   ├── trading/      # 트레이딩 엔진, 업비트 클라이언트
│   │   ├── services/     # 알림(텔레그램, FCM) 등
│   │   └── ...
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
├── upbit_trading_app/    # Flutter Android 앱
│   ├── lib/
│   └── pubspec.yaml
├── docs/                 # 기획·배포·트레이딩 로직 문서
│   ├── 배포_가이드.md
│   ├── 서버_설치_Jetson_Tailscale.md
│   ├── 트레이딩_로직_상세_가이드.md
│   └── 진입_매각_다중확인_로직.md
└── README.md
```

---

## 📄 문서 링크

| 문서 | 설명 |
|------|------|
| [트레이딩_로직_상세_가이드.md](docs/트레이딩_로직_상세_가이드.md) | **진입·매각 로직을 아주 길고 친절하게** 설명 (예시, FAQ 포함) |
| [배포_가이드.md](docs/배포_가이드.md) | 환경변수, CORS, systemd, Docker, 점검 체크리스트 |
| [서버_설치_Jetson_Tailscale.md](docs/서버_설치_Jetson_Tailscale.md) | Jetson + Tailscale로 서버 세팅·SSH·앱 연결 |
| [진입_매각_다중확인_로직.md](docs/진입_매각_다중확인_로직.md) | 진입/매각 2~3단계 확인 설계 요약 |
| [APK_빌드_및_배포.md](docs/APK_빌드_및_배포.md) | APK 직접 빌드·GitHub Release 업로드 방법 |
| [API_명세서.md](docs/API_명세서.md) | 백엔드 API 요약 |

---

## ⚠️ 면책

자동매매로 인한 손실은 **사용자 책임**이며, 본 프로젝트는 투자 결과에 대해 책임지지 않습니다.  
업비트 API 이용 시 업비트 이용약관 및 정책을 준수해 주세요.

---

## 📌 라이선스·저작자

**저작자**: 차리 (challychoi@me.com)  
배짱이 v1.0 — 업비트 현물 자동매매 앱 및 백엔드.
