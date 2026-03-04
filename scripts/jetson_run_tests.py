#!/usr/bin/env python3
"""Jetson 서버에서 메일/텔레그램 테스트 및 로그인 API 테스트. SSH로 원격 실행 후 로컬에서 curl로 로그인 검사."""
import os
import sys

def run_ssh(cmd, password, host="100.80.178.45", user="upbit"):
    try:
        import paramiko
    except ImportError:
        return -1, "", "paramiko 미설치"
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        c.connect(host, username=user, password=password, timeout=15)
        _, out, err = c.exec_command(cmd)
        return out.channel.recv_exit_status(), out.read().decode("utf-8", errors="replace"), err.read().decode("utf-8", errors="replace")
    finally:
        c.close()

def main():
    password = os.environ.get("JETSON_SSH_PASSWORD", "").strip()
    if not password:
        import getpass
        password = getpass.getpass("Jetson SSH 비밀번호: ")
    host, user = "100.80.178.45", "upbit"

    print("=== 1. 메일 테스트 (서버에서 baejjangi test mail) ===")
    code, out, err = run_ssh(
        "cd /home/upbit/baejjangi/backend && source venv/bin/activate && echo test@example.com | timeout 15 python baejjangi.py test mail 2>&1",
        password, host, user
    )
    print(out or err)
    print("exit:", code, "\n")

    print("=== 2. 텔레그램 테스트 (서버에서 baejjangi test telegram) ===")
    code2, out2, err2 = run_ssh(
        "cd /home/upbit/baejjangi/backend && source venv/bin/activate && timeout 10 python baejjangi.py test telegram 2>&1",
        password, host, user
    )
    print(out2 or err2)
    print("exit:", code2, "\n")

    print("=== 3. 로그인 API (로컬 curl) - 엔드포인트 응답 확인용 ===")
    import urllib.request
    import json
    req = urllib.request.Request(
        "http://100.80.178.45:8000/api/v1/auth/login",
        data=json.dumps({"email": "wrong@x.com", "password": "wrong"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            print("status:", r.status, r.read().decode()[:200])
    except urllib.error.HTTPError as e:
        print("status:", e.code, "(예상: 401 등) - 로그인 엔드포인트 동작함. body:", e.read().decode()[:150])
    except Exception as e:
        print("error:", e)
    print("\n완료.")

if __name__ == "__main__":
    main()
