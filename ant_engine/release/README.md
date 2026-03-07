# 개미엔진(AntEngine) 릴리스 바이너리

- **AntEngine-버전.exe**: Windows 로컬/개발용. (예: AntEngine-1.1.exe)
- **AntEngine-버전.bin**: Linux ARM64(aarch64)용. Jetson 등 서버에서 실행. (예: AntEngine-1.1.bin)
- 빌드: Windows는 `ant_engine/build`에서 cmake --build . --config Release. Linux .bin은 Jetson에서 `scripts/jetson_build_ant_engine.py` 실행 후 `scripts/jetson_fetch_ant_engine_bin.py`로 이 폴더에 받아옴.
- 실행: Windows `AntEngine-1.1.exe`, Linux `./AntEngine-1.1.bin` (기본 포트 9100)

**GitHub 업데이트 시**: 버전 업할 때마다 해당 버전 바이너리(.exe 또는 .bin)를 **함께** 커밋·푸시.
