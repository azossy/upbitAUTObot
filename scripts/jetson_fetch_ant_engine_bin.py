#!/usr/bin/env python3
"""
Jetson 서버에서 AntEngine-버전.bin 을 로컬로 다운로드.
다운로드 위치: ant_engine/release/AntEngine-버전.bin (GitHub 커밋 가능)

사용법 (프로젝트 루트에서):
  JETSON_SSH_PASSWORD=비밀번호 python scripts/jetson_fetch_ant_engine_bin.py
"""
import os
import re
import sys

def get_engine_version():
    """ant_engine/CMakeLists.txt 에서 project(ant_engine VERSION x.y) 파싱."""
    root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    cmake = os.path.join(root, "ant_engine", "CMakeLists.txt")
    if not os.path.isfile(cmake):
        return "0.9"
    with open(cmake, "r", encoding="utf-8") as f:
        for line in f:
            if "project(ant_engine VERSION" in line or "project(ant_engine  VERSION" in line:
                m = re.search(r"VERSION\s+([\d.]+)", line)
                if m:
                    return m.group(1).strip()
    return "0.9"


def main():
    password = os.environ.get("JETSON_SSH_PASSWORD", "").strip()
    if not password:
        import getpass
        password = getpass.getpass("Jetson SSH 비밀번호: ")

    try:
        import paramiko
    except ImportError:
        print("paramiko 미설치. pip install paramiko 후 재실행.")
        sys.exit(1)

    version = get_engine_version()
    bin_name = f"AntEngine-{version}.bin"
    host = "100.80.178.45"
    user = "upbit"
    remote_path = f"/home/upbit/baejjangi/ant_engine/build/{bin_name}"
    root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    release_dir = os.path.join(root, "ant_engine", "release")
    local_path = os.path.join(release_dir, bin_name)

    os.makedirs(release_dir, exist_ok=True)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=user, password=password, timeout=30)
        sftp = client.open_sftp()
        sftp.get(remote_path, local_path)
        sftp.close()
        client.close()
        size = os.path.getsize(local_path)
        print("다운로드 완료.")
        print("  로컬 경로:", os.path.abspath(local_path))
        print("  크기:", size, "bytes")
        print("  이 파일을 git add 후 커밋하면 GitHub에 올라갑니다.")
    except FileNotFoundError:
        print(f"Jetson에 {bin_name} 없음. 먼저 scripts/jetson_build_ant_engine.py 로 빌드하세요.")
        sys.exit(1)
    except Exception as e:
        print("실패:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
