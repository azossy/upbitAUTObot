# 개미엔진(AntEngine) 릴리스 바이너리

- **AntEngine-버전.bin** (예: AntEngine-1.0.bin): Linux ARM64(aarch64)용 빌드. Jetson 등에서 실행.
- 빌드: Jetson에서 `scripts/jetson_build_ant_engine.py` 실행 후 `scripts/jetson_fetch_ant_engine_bin.py`로 이 폴더에 받아옴.
- 실행: `./AntEngine-1.0.bin` (기본 포트 9100)

**GitHub 업데이트 시**: 이 바이너리 파일을 **항상 함께** 커밋·푸시. 없으면 클론/다운로드한 환경에서 엔진을 실행할 수 없음.
