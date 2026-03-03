# 배짱이 (Baejjangi) — 업비트 현물 자동매매

**저작자**: 차리 (challychoi@me.com)

업비트 거래소 **현물** 자동매매를 스마트폰 앱으로 제어·모니터링하는 시스템입니다.  
서버(Jetson Orin Nano, PC 등)에서 24시간 봇을 돌리고, Android 앱으로 시작/정지·설정·잔고·포지션·푸시 알림을 받을 수 있습니다.

---

## 📱 빠른 설치 (Quick Start)

### 1. Android 앱 설치

- **[Releases](https://github.com/azossy/upbitAUTObot/releases)** 에서 최신 버전의 `app-release.apk` 를 다운로드합니다.
- Android 기기에 APK를 복사한 뒤 설치합니다. (설치 시 "알 수 없는 앱" 허용 필요할 수 있음)
- 앱 실행 후 **설정 → API 서버 주소**에 본인이 운영하는 서버 주소를 입력합니다. (예: `http://서버IP:8000`)

### 2. 서버 한 줄 요약

```bash
# 서버(Ubuntu/Jetson)에서
git clone https://github.com/azossy/upbitAUTObot.git && cd upbitAUTObot/backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # JWT_SECRET_KEY, ENCRYPTION_KEY 등 수정 필수
uvicorn main:app --host 0.0.0.0 --port 8000
```

자세한 서버 설치(Tailscale, systemd 등)는 [docs/서버_설치_Jetson_Tailscale.md](docs/서버_설치_Jetson_Tailscale.md) 와 [docs/배포_가이드.md](docs/배포_가이드.md) 를 참고하세요.

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
진입(매수)과 매각(매도) 시점을 **2~3단계 확인**으로 판단해, 단일 신호로 인한 오진·과매매를 줄이도록 설계되어 있습니다.

### 진입 시점 (매수) — 3단계 확인

매수는 **1차 → 2차 → 3차**를 **모두** 통과할 때만 실행합니다. 한 단계라도 통과하지 않으면 진입하지 않습니다.

| 단계 | 확인 내용 | 통과 조건 요약 |
|------|-----------|----------------|
| **1차** | 시장 국면 | 현재 모드가 **상승장**이고, 투자 가능 슬롯이 있을 것. (하락·횡보에서는 진입 금지) |
| **2차** | 코인별 추세 | ① 1시간봉 EMA 골든크로스 ② 4시간봉 EMA 정배열 ③ ADX 25 이상 ④ 골든크로스 구간 거래량 > 20기간 평균 — **네 가지 모두 충족** |
| **3차** | 진입 타이밍 | **A안(눌림목)**: 단기 EMA까지 되돌림 + RSI 50 이하 + 거래량 평균 이하 후 진입. **B안(강한 추세)**: 시장 점수 +8, ADX 35 이상, BTC 1분봉 3연속 양봉 등 조건 시 눌림목 없이 진입 |

- **진입 금지 조건**: 유의종목, 급락 코인, 대규모 청산 직후, 당일 손절 이력 등은 1차와 함께 상시 체크합니다.
- **분할 진입**: 1차 40% → 2차 35% → 3차 25%처럼 구간을 나누어 리스크를 분산할 수 있도록 설계합니다.

### 매각 시점 (매도) — 우선순위 + 2~3단계 확인

매각은 **즉시 전량 매각**과 **분할 익절·시간 손절**로 구분하며, 우선순위가 높은 조건부터 검사합니다.

**즉시 전량 매각 (1~3순위, 2단계 확인 권장)**

| 순위 | 조건 | 1차 확인 | 2차 확인(권장) |
|------|------|----------|----------------|
| 1순위 | 국면 하락 전환 | 시장 점수 하락 범위 진입 | **연속 2회** 또는 1회 + 5분 후 재계산 동일 시 전량 시장가 청산 |
| 2순위 | 손절 -2.5% | 진입 평균가 대비 -2.5% 도달 | 해당 캔들 종가 또는 1봉 뒤 유지 시 시장가 청산 (일시 스프레드 오진 방지) |
| 3순위 | 데드크로스 | 1시간봉 EMA 데드크로스 | 다음 1봉 종가가 단기선 아래 유지 또는 ADX 25 미만 시 전량 시장가 청산 |

**분할 익절 (4~6순위)**  
평균가 대비 +5% / +10% / +15% 구간 도달 시, **해당 % 이상이 1봉(또는 N분) 유지**할 때만 해당 비율만큼 지정가/시장가 청산합니다. (순간 스파이크로 익절하지 않도록 2단계 확인)

**시간 손절 (7순위, 3단계)**  
진입 후 12시간 경과 + 수익률 -0.5% ~ +1.5% 구간 + **국면 점수가 진입 시점 대비 -2점 이상 하락**(또는 ADX 20 이하) — **세 가지 모두** 충족 시에만 시간 손절 실행. 미충족 시 4시간 연장 후 재판단(최대 1회).

### 사용 지표·기법 요약

- **EMA**: 1시간봉·4시간봉 골든/데드크로스, 정배열로 추세 판단.
- **ADX**: 추세 강도(25 이상 진입, 25 미만 시 데드크로스 청산 등).
- **거래량**: 골든크로스 구간에서 20기간 평균 대비 거래량 확인, 눌림목 시 거래량 평균 이하 후 진입.
- **RSI**: 눌림목 진입 시 50 이하 등으로 과매수/과매도 보조.
- **시장 점수**: 상승/횡보/하락 국면 판단, 하락 전환 시 연속 2회 등 2단계 확인 후 청산.

상세 설계는 [docs/진입_매각_다중확인_로직.md](docs/진입_매각_다중확인_로직.md), [docs/종목선정_비중_거래소참조.md](docs/종목선정_비중_거래소참조.md) 에 정리되어 있습니다.

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

**방법 B: 직접 빌드**

```bash
cd upbit_trading_app
flutter pub get
flutter build apk --release
```

생성된 APK 경로: `build/app/outputs/flutter-apk/app-release.apk`  
이 파일을 Android 기기로 복사해 설치하면 됩니다.

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
│   └── 진입_매각_다중확인_로직.md
└── README.md
```

---

## 📄 문서 링크

| 문서 | 설명 |
|------|------|
| [배포_가이드.md](docs/배포_가이드.md) | 환경변수, CORS, systemd, Docker, 점검 체크리스트 |
| [서버_설치_Jetson_Tailscale.md](docs/서버_설치_Jetson_Tailscale.md) | Jetson + Tailscale로 서버 세팅·SSH·앱 연결 |
| [진입_매각_다중확인_로직.md](docs/진입_매각_다중확인_로직.md) | 진입/매각 2~3단계 확인 상세 설계 |
| [API_명세서.md](docs/API_명세서.md) | 백엔드 API 요약 |

---

## ⚠️ 면책

자동매매로 인한 손실은 **사용자 책임**이며, 본 프로젝트는 투자 결과에 대해 책임지지 않습니다.  
업비트 API 이용 시 업비트 이용약관 및 정책을 준수해 주세요.

---

## 📌 라이선스·저작자

**저작자**: 차리 (challychoi@me.com)  
배짱이 v1.0 — 업비트 현물 자동매매 앱 및 백엔드.
