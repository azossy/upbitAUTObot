#!/usr/bin/env python3
"""
Jetson 서버: git pull + 서비스 재시작 + health 확인. .env 등 환경설정은 건드리지 않음.
실행: JETSON_SSH_PASSWORD=비밀번호 python scripts/jetson_update_only.py
또는: python scripts/jetson_update_only.py  (프롬프트에서 비밀번호 입력)
"""
import os
import sys

def run_ssh(cmd: str, password: str, host: str = "100.80.178.45", user: str = "upbit", wait_sudo: bool = False) -> tuple[int, str, str]:
    try:
        import paramiko
    except ImportError:
        return -1, "", "paramiko 미설치. pip install paramiko 후 재실행."
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=user, password=password, timeout=15)
        stdin, stdout, stderr = client.exec_command(cmd, get_pty=wait_sudo)
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


def main():
    password = os.environ.get("JETSON_SSH_PASSWORD", "").strip()
    if not password:
        import getpass
        password = getpass.getpass("Jetson SSH 비밀번호: ")

    host = "100.80.178.45"
    user = "upbit"

    print("=== Jetson 업데이트 (환경설정 .env 미변경) ===\n")

    # 1. git pull
    print("[1/4] git pull ...")
    code, out, err = run_ssh("cd /home/upbit/baejjangi && git pull", password, host, user)
    if code != 0:
        print("  실패:", (out or err).strip()[:400])
        sys.exit(1)
    print("  OK:", (out or err).strip().split("\n")[0][:80])

    # 2. pip install (의존성 갱신)
    print("\n[2/4] pip install -r requirements.txt ...")
    code2, out2, err2 = run_ssh(
        "cd /home/upbit/baejjangi/backend && (test -f venv/bin/pip && ./venv/bin/pip install -q -r requirements.txt || pip3 install -q -r requirements.txt)",
        password, host, user
    )
    if code2 != 0:
        print("  경고:", (out2 or err2).strip()[:200])
    else:
        print("  OK")

    # 3. 서비스 재시작
    print("\n[3/4] systemctl restart baejjangi-backend ...")
    code3, out3, err3 = run_ssh("sudo -n systemctl restart baejjangi-backend 2>/dev/null; echo EXIT=$?", password, host, user)
    if "EXIT=0" not in (out3 or ""):
        code3, out3, err3 = run_ssh("sudo systemctl restart baejjangi-backend", password, host, user, wait_sudo=True)
    if code3 != 0:
        print("  실패:", (out3 or err3).strip()[:200])
        sys.exit(1)
    print("  OK")
    import time
    time.sleep(5)

    # 4. health
    print("\n[4/4] health 확인 ...")
    code4, out4, _ = run_ssh("curl -s http://127.0.0.1:8000/health", password, host, user)
    if code4 == 0 and out4 and "ok" in out4.lower():
        print("  정상:", out4.strip()[:120])
        print("\n" + "=" * 50)
        print("  Jetson 업데이트 완료. 환경설정(.env)은 변경하지 않았습니다.")
        print("=" * 50)
    else:
        print("  응답:", (out4 or "(없음)").strip()[:200])
        print("\n  서비스 상태 확인: ssh upbit@100.80.178.45 'sudo journalctl -u baejjangi-backend -n 20 --no-pager'")
        sys.exit(1)


if __name__ == "__main__":
    main()
