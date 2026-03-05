# 개미엔진 (AntEngine) v0.9 — C++

트레이딩 시그널 엔진. **C++17**, 단일 바이너리 배포. 입·출력 규격은 [트레이딩_엔진_입출력_연동_가이드.md](../docs/트레이딩_엔진_입출력_연동_가이드.md) 준수.

**버전**: 빌드할 때마다 **0.1**씩 올림 (예: 0.9 → 1.0). `CMakeLists.txt`의 `project(ant_engine VERSION x.y)` 수정.

## 요구사항

- CMake 3.14+
- C++17 지원 컴파일러 (MSVC, GCC, Clang)
- (의존성은 CMake FetchContent로 자동 다운로드: nlohmann/json, cpp-httplib)

## 빌드

### Windows (Visual Studio 설치된 경우)

**방법 1 — 개발자 명령 프롬프트에서**

1. 시작 메뉴에서 **「개발자 명령 프롬프트 for VS 2022」** 또는 **「x64 Native Tools Command Prompt for VS 2022」** 실행.
2. 프로젝트 루트로 이동 후:

```cmd
cd ant_engine
mkdir build
cd build
cmake ..
cmake --build . --config Release
```

실행 파일: `build\Release\ant_engine.exe`

**방법 2 — Visual Studio IDE에서**

1. Visual Studio에서 **파일 → 열기 → 폴더** 로 `ant_engine` 폴더 선택.
2. CMake 프로젝트로 인식되면 상단 **구성** 에서 `Release`, 대상 `ant_engine` 선택.
3. **빌드 → ant_engine 빌드** (또는 Ctrl+Shift+B).  
   출력: `out\build\x64-Release\ant_engine.exe` 등 (구성에 따라 다름).

### Windows (Visual Studio가 감지되지 않을 때 — MinGW)

MinGW(GCC)가 PATH에 있으면:

```cmd
cd ant_engine
mkdir build && cd build
cmake .. -G "MinGW Makefiles" -DCMAKE_CXX_COMPILER=g++
mingw32-make -j4
```
실행 파일: `build\ant_engine.exe`

### Linux (서버·Jetson) — 출력: AntEngine-버전.bin

**로컬에서 Jetson SSH로 빌드 (권장):**

```bash
# 프로젝트 루트에서 (비밀번호는 프롬프트 또는 JETSON_SSH_PASSWORD)
python scripts/jetson_build_ant_engine.py
```

- Jetson에 ant_engine 소스가 없으면 로컬 `ant_engine/` 폴더를 업로드한 뒤 빌드.
- 결과: `ant_engine/build/AntEngine-0.9.bin` (ELF 64-bit, ARM aarch64). 로컬로 받기: `python scripts/jetson_fetch_ant_engine_bin.py`

**Jetson에 직접 SSH 접속 후 빌드:**

```bash
ssh upbit@100.80.178.45
cd /home/upbit/baejjangi/ant_engine   # 또는 git pull 후
mkdir -p build && cd build
cmake .. && make -j$(nproc)
# 출력: ./AntEngine-0.9.bin
```

### macOS

```bash
cd ant_engine && mkdir build && cd build
cmake .. && cmake --build .
# 실행: ./ant_engine (macOS는 OUTPUT_NAME 변경 없음)
```

## 실행

```bash
# 기본 포트 9100
./AntEngine-0.9.bin   # Linux 서버 (Jetson)
./ant_engine          # macOS
ant_engine.exe        # Windows

# 포트 지정
# Windows (PowerShell): $env:ANT_ENGINE_PORT="9101"; .\ant_engine.exe
# Linux: ANT_ENGINE_PORT=9101 ./AntEngine-0.9.bin
```

## API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | /health | 헬스체크. `{"status":"ok"}` |
| GET | /version | 엔진 버전. `engine`, `version`, `schema_version` |
| POST | /signal | 시그널 요청. Body: 입출력 가이드 §2 JSON → §3 JSON 응답 |

## v0.9 동작 요약

- **입력 검증**: market, mode 필수. 잘못되면 `status: "error"`.
- **이벤트 창**: `config.event_window_active == true` 이면 진입 보류 (`hold_event_window`).
- **매각**: 보유 포지션에 대해 손절(`stop_loss_pct`)/익절(`take_profit_pct`) 조건 시 `sell` 시그널.
- **진입**: 1시간봉 24개 미만이면 보류. 현재는 1차 조건 골격만 두고 보류(`hold_no_signal`) — 추후 확장.

## 문서

- [트레이딩_엔진_상세_기획서.md](../docs/트레이딩_엔진_상세_기획서.md) — 기획·팩터·바이너리 분리
- [트레이딩_엔진_입출력_연동_가이드.md](../docs/트레이딩_엔진_입출력_연동_가이드.md) — 입·출력 리스트·연동 방법
- [개미엔진_AntEngine.md](../docs/개미엔진_AntEngine.md) — 개미엔진 프로젝트 설명
