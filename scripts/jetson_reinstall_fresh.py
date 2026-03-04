#!/usr/bin/env python3
"""
Jetson 서버: 기존 설치 제거 후 최신 버전으로 새로 클론·빌드.
운영 설정(.env, DB)은 백업 후 그대로 복원해서 재입력 없이 사용.

실행: 프로젝트 루트에서
  JETSON_SSH_PASSWORD=비밀번호 python scripts/jetson_reinstall_fresh.py
  또는 비밀번호 입력 프롬프트: python scripts/jetson_reinstall_fresh.py
"""
import os
import sys

def run_ssh(cmd: str, password: str, host: str, user: str, wait_sudo: bool = False) -> tuple[int, str, str]:
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

    def step(name: str, cmd: str, need_sudo: bool = False):
        code, out, err = run_ssh(cmd, password, host, user, wait_sudo=need_sudo)
        print(f"[{name}] exit={code}")
        if out.strip():
            print(out.strip())
        if err.strip():
            print("stderr:", err.strip(), file=sys.stderr)
        return code

    print("1. 백업 .env 및 DB ...")
    code = step("백업", """
BACKUP_DIR="/tmp/baejjangi_reinstall_backup"
rm -rf "$BACKUP_DIR"
mkdir -p "$BACKUP_DIR"
for base in /home/upbit/upbitAUTObot /home/upbit/baejjangi; do
  if [ -f "$base/backend/.env" ]; then cp -a "$base/backend/.env" "$BACKUP_DIR/.env"; echo "OK .env"; break; fi
done
for base in /home/upbit/upbitAUTObot /home/upbit/baejjangi; do
  if ls "$base/backend"/*.db 1>/dev/null 2>&1; then cp -a "$base/backend"/*.db "$BACKUP_DIR/"; echo "OK db"; break; fi
done
ls -la "$BACKUP_DIR" 2>/dev/null || true
""")
    if code != 0:
        print("백업 단계 실패. 계속할까요? (기존 .env 없을 수 있음)")
    print()

    print("2. 서비스 중지 ...")
    step("stop", "sudo systemctl stop baejjangi-backend 2>/dev/null || true", need_sudo=True)
    print()

    print("3. 기존 설치 폴더 삭제 ...")
    step("삭제", "rm -rf /home/upbit/upbitAUTObot /home/upbit/baejjangi")
    print()

    print("4. 최신 저장소 클론 (baejjangi) ...")
    code = step("clone", "cd /home/upbit && git clone https://github.com/azossy/upbitAUTObot.git baejjangi")
    if code != 0:
        print("clone 실패.", file=sys.stderr)
        sys.exit(1)
    print()

    print("5. 설정 복원 (.env, DB) ...")
    step("복원", """
BACKUP_DIR="/tmp/baejjangi_reinstall_backup"
if [ -f "$BACKUP_DIR/.env" ]; then
  cp -a "$BACKUP_DIR/.env" /home/upbit/baejjangi/backend/.env
  echo "RESTORED .env"
else
  cp /home/upbit/baejjangi/backend/.env.example /home/upbit/baejjangi/backend/.env
  echo "No backup .env -> .env.example 복사 (JWT/ENCRYPTION 등 수동 설정 필요)"
fi
if ls "$BACKUP_DIR"/*.db 1>/dev/null 2>&1; then
  cp -a "$BACKUP_DIR"/*.db /home/upbit/baejjangi/backend/
  echo "RESTORED DB"
fi
rm -rf "$BACKUP_DIR"
""")
    print()

    print("6. 가상환경 + pip install ...")
    code = step("venv", "cd /home/upbit/baejjangi/backend && python3 -m venv venv && ./venv/bin/pip install -q -r requirements.txt")
    if code != 0:
        print("venv/pip 실패.", file=sys.stderr)
        sys.exit(1)
    print()

    print("7. systemd: 서비스 파일명 baejjangi-backend.service 로 통일 ...")
    step("systemd", "sudo test -f /etc/systemd/system/upbit-backend.service && sudo mv /etc/systemd/system/upbit-backend.service /etc/systemd/system/baejjangi-backend.service || true; sudo sed -i 's|upbitAUTObot/backend|baejjangi/backend|g' /etc/systemd/system/baejjangi-backend.service 2>/dev/null; sudo systemctl daemon-reload", need_sudo=True)
    print()

    print("8. 서비스 기동 ...")
    step("start", "sudo systemctl start baejjangi-backend", need_sudo=True)
    import time
    time.sleep(4)
    code, out, _ = run_ssh("curl -s http://127.0.0.1:8000/health", password, host, user)
    print("health:", out.strip() if out else "(none)")
    code2, out2, _ = run_ssh("systemctl is-active baejjangi-backend", password, host, user)
    print("systemctl is-active:", out2.strip())

    if "ok" in (out or "").lower() or "200" in (out or ""):
        print("\n정상 기동됨. 확인: curl -s http://100.80.178.45:8000/health")
    else:
        print("\n상태 확인: ssh upbit@100.80.178.45 'sudo journalctl -u baejjangi-backend -n 30 --no-pager'")

if __name__ == "__main__":
    main()
