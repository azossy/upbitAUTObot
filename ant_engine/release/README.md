# 개미엔진(AntEngine) 릴리스 바이너리

**배포 형식: AntEngine-버전정보.bin** (Linux 서버용). 파일명 규칙을 반드시 준수.

- **GitHub에 올리는 것**: **AntEngine-버전정보.bin** 만. (예: AntEngine-1.1.bin)
- **올리지 않는 것**: .exe(로컬 시뮬레이션용 엔진은 로컬에서만 실행, GitHub 미배포)
- **AntEngine-버전정보.bin**: Linux ARM64(aarch64)용. Jetson 등 서버에서 실행.
- 빌드: .bin은 Jetson에서 `scripts/jetson_build_ant_engine.py` 실행 후 `scripts/jetson_fetch_ant_engine_bin.py`로 이 폴더에 받아옴. Windows에서 빌드한 .exe는 자체 시뮬레이션용으로만 로컬 사용.
- 실행: Linux `./AntEngine-1.1.bin` (기본 포트 9100)

**GitHub 업데이트 시**: 버전 올릴 때마다 **AntEngine-버전정보.bin** 만 커밋·푸시. (.exe는 올리지 않음)
