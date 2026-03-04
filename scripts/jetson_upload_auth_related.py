#!/usr/bin/env python3
"""Jetson에 인증 메일 관련 파일 일괄 업로드 후 재시작. JETSON_SSH_PASSWORD 환경변수 또는 프롬프트."""
import os
import sys

def main():
    try:
        import paramiko
    except ImportError:
        print("pip install paramiko 후 재실행"); sys.exit(1)
    password = os.environ.get("JETSON_SSH_PASSWORD", "").strip() or __import__("getpass").getpass("Jetson SSH 비밀번호: ")
    host, user = "100.80.178.45", "upbit"
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "app"))
    files = [
        ("routers/auth.py", "/home/upbit/upbitAUTObot/backend/app/routers/auth.py"),
        ("schemas/auth.py", "/home/upbit/upbitAUTObot/backend/app/schemas/auth.py"),
        ("models/email_verification.py", "/home/upbit/upbitAUTObot/backend/app/models/email_verification.py"),
        ("services/email_service.py", "/home/upbit/upbitAUTObot/backend/app/services/email_service.py"),
    ]
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, password=password, timeout=15)
    sftp = client.open_sftp()
    for rel, remote in files:
        local = os.path.join(base, os.path.normpath(rel))
        if os.path.isfile(local):
            sftp.put(local, remote)
            print(f"  OK: {rel} -> Jetson")
        else:
            print(f"  SKIP: {local} 없음")
    sftp.close()
    stdin, stdout, stderr = client.exec_command("sudo -n systemctl restart upbit-backend 2>/dev/null; sleep 1; echo PASS | sudo -S systemctl restart upbit-backend 2>/dev/null; sleep 5; systemctl is-active upbit-backend", get_pty=True)
    import time
    time.sleep(0.5)
    stdin.write(password + "\n")
    stdin.flush()
    out = stdout.read().decode("utf-8", errors="replace")
    client.close()
    print("\n재시작 결과:", out.strip())
    print("\n확인: curl -s http://100.80.178.45:8000/health")

if __name__ == "__main__":
    main()
