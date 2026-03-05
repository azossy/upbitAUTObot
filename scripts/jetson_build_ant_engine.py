#!/usr/bin/env python3
"""
Jetson 서버에 SSH 접속해 ant_engine(개미엔진)을 Linux용으로 빌드.
출력: AntEngine-버전.bin (예: ant_engine/build/AntEngine-0.9.bin)

사용법 (프로젝트 루트에서):
  JETSON_SSH_PASSWORD=비밀번호 python scripts/jetson_build_ant_engine.py
  또는: python scripts/jetson_build_ant_engine.py  (비밀번호 프롬프트)
"""
import os
import sys

def run_ssh(cmd: str, password: str, host: str = "100.80.178.45", user: str = "upbit", wait_sudo: bool = False) -> tuple:
    try:
        import paramiko
    except ImportError:
        return -1, "", "paramiko 미설치. pip install paramiko 후 재실행."
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=user, password=password, timeout=30)
        stdin, stdout, stderr = client.exec_command(cmd, get_pty=wait_sudo, timeout=300)
        if wait_sudo and password:
            import time
            time.sleep(0.5)
            stdin.write(password + "\n")
            stdin.flush()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        code = stdout.channel.recv_exit_status()
        return code, out, err
    except Exception as e:
        return -1, "", str(e)
    finally:
        client.close()


def upload_ant_engine(password: str, host: str, user: str):
    """로컬 ant_engine 폴더를 Jetson /home/upbit/baejjangi/ant_engine 에 업로드."""
    try:
        import paramiko
    except ImportError:
        return False, "paramiko 미설치"
    root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    local_dir = os.path.join(root, "ant_engine")
    if not os.path.isdir(local_dir):
        return False, "ant_engine 폴더 없음"
    remote_base = "/home/upbit/baejjangi/ant_engine"
    exclude = {"build", ".git", "__pycache__", ".vs", "out"}
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=user, password=password, timeout=30)
        sftp = client.open_sftp()
        def mkdir_r(sftp, path):
            parts = path.replace("\\", "/").rstrip("/").split("/")
            for i in range(1, len(parts) + 1):
                p = "/".join(parts[:i])
                if p and p != ".":
                    try:
                        sftp.stat(p)
                    except FileNotFoundError:
                        sftp.mkdir(p)
        mkdir_r(sftp, remote_base)
        uploaded = 0
        for dirpath, dirnames, filenames in os.walk(local_dir):
            rel = os.path.relpath(dirpath, local_dir)
            if rel == ".":
                rel_parts = []
            else:
                rel_parts = [p for p in rel.split(os.sep) if p and p not in exclude]
            dirnames[:] = [d for d in dirnames if d not in exclude]
            remote_dir = remote_base if not rel_parts else (remote_base + "/" + "/".join(rel_parts))
            try:
                sftp.stat(remote_dir)
            except FileNotFoundError:
                mkdir_r(sftp, remote_dir)
            for f in filenames:
                local_path = os.path.join(dirpath, f)
                remote_path = remote_dir + "/" + f
                sftp.put(local_path, remote_path)
                uploaded += 1
        sftp.close()
        client.close()
        return True, f"업로드 {uploaded}개 파일"
    except Exception as e:
        return False, str(e)
    finally:
        try:
            client.close()
        except Exception:
            pass


def get_engine_version():
    """ant_engine/CMakeLists.txt 에서 project(ant_engine VERSION x.y) 파싱."""
    root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    cmake = os.path.join(root, "ant_engine", "CMakeLists.txt")
    if not os.path.isfile(cmake):
        return "0.9"
    with open(cmake, "r", encoding="utf-8") as f:
        for line in f:
            if "project(ant_engine VERSION" in line or "project(ant_engine  VERSION" in line:
                import re
                m = re.search(r"VERSION\s+([\d.]+)", line)
                if m:
                    return m.group(1).strip()
    return "0.9"


def main():
    password = os.environ.get("JETSON_SSH_PASSWORD", "").strip()
    if not password:
        import getpass
        password = getpass.getpass("Jetson SSH 비밀번호: ")

    host = "100.80.178.45"
    user = "upbit"
    version = get_engine_version()
    bin_name = f"AntEngine-{version}.bin"

    print("1. Jetson 연결 및 ant_engine 소스 업로드 ...")
    ok, msg = upload_ant_engine(password, host, user)
    if not ok:
        print("   실패:", msg)
        sys.exit(1)
    print("   ", msg)

    print("2. cmake/build-essential 설치 여부 ...")
    code, out, err = run_ssh("which cmake && which g++ && echo OK || echo INSTALL", password, host, user)
    if "OK" not in out:
        print("   cmake/g++ 설치 중 (sudo) ...")
        code, out, err = run_ssh("sudo apt-get update && sudo apt-get install -y cmake build-essential", password, host, user, wait_sudo=True)
        if code != 0:
            print("   설치 실패:", (out + err)[:500])
            sys.exit(1)
        print("   설치 완료.")
    else:
        print("   OK")

    print(f"3. ant_engine 빌드 (Linux → {bin_name}) ...")
    cmd = (
        "cd /home/upbit/baejjangi/ant_engine && "
        "rm -rf build && mkdir -p build && cd build && "
        "cmake .. && make -j$(nproc)"
    )
    code, out, err = run_ssh(cmd, password, host, user)
    if code != 0:
        print("   빌드 실패.")
        print(out[-2000:] if len(out) > 2000 else out)
        print(err[-1000:] if len(err) > 1000 else err)
        sys.exit(1)
    print("   빌드 완료.")

    print("4. 출력 파일 확인 ...")
    remote_bin = f"/home/upbit/baejjangi/ant_engine/build/{bin_name}"
    code, out, err = run_ssh(f"ls -la {remote_bin} 2>/dev/null && file {remote_bin}", password, host, user)
    if code != 0 or bin_name not in out:
        print(f"   {bin_name} 없음. build 폴더 목록:")
        run_ssh("ls -la /home/upbit/baejjangi/ant_engine/build/", password, host, user)
        sys.exit(1)
    print(out.strip())
    print("\n=== 완료 ===")
    print(f"  경로: {remote_bin}")
    print(f"  실행: {remote_bin}")
    print("  포트 기본 9100, 변경: ANT_ENGINE_PORT=9101 ./" + bin_name)


if __name__ == "__main__":
    main()
