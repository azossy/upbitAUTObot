#!/usr/bin/env python3
"""
Jetson 서버에 SSH 접속해 전 항목 점검·문제 시 조치 후 결과 보고.
실행: JETSON_SSH_PASSWORD=비밀번호 python scripts/jetson_full_check_and_fix.py
또는: python scripts/jetson_full_check_and_fix.py  (프롬프트에서 비밀번호 입력)
"""
import os
import sys
import subprocess

def run_ssh(cmd: str, password: str, host: str = "100.80.178.45", user: str = "upbit", wait_sudo: bool = False) -> tuple[int, str, str]:
    """paramiko로 SSH 실행. (pip install paramiko 필요)"""
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
    report = []

    # 1. .env 존재
    code, out, err = run_ssh("test -f /home/upbit/upbitAUTObot/backend/.env && echo OK || echo MISSING", password, host, user)
    env_ok = "OK" in out
    report.append(("1. .env 존재", "OK" if env_ok else "MISSING", out.strip() or err.strip()))

    # 2. JWT/ENCRYPTION 기본값 아님
    code, out, err = run_ssh(
        "grep -E '^(JWT_SECRET_KEY|ENCRYPTION_KEY)=' /home/upbit/upbitAUTObot/backend/.env 2>/dev/null | sed 's/=.*/=***/'",
        password, host, user
    )
    has_secrets = "JWT_SECRET_KEY" in out and "ENCRYPTION_KEY" in out
    report.append(("2. JWT/ENCRYPTION 설정", "OK" if has_secrets else "확인 필요", out.strip() or "(없음)"))

    # 3. 코드 최신 (auth에 send-verification-email 있는지)
    code, out, err = run_ssh(
        "grep -q 'send-verification-email' /home/upbit/upbitAUTObot/backend/app/routers/auth.py 2>/dev/null && echo HAS_ROUTE || echo OLD"
        , password, host, user
    )
    has_route = "HAS_ROUTE" in out
    report.append(("3. 인증메일 라우트(코드)", "OK" if has_route else "구버전", out.strip()))

    # 4. 갱신: git pull
    if not has_route:
        code, out, err = run_ssh(
            "cd /home/upbit/upbitAUTObot && git pull",
            password, host, user
        )
        report.append(("4. git pull", "OK" if code == 0 else "실패", (out.strip() or err.strip())[:300]))
        code2, out2, _ = run_ssh(
            "grep -q 'send-verification-email' /home/upbit/upbitAUTObot/backend/app/routers/auth.py 2>/dev/null && echo HAS || echo NO",
            password, host, user
        )
        if "HAS" not in out2:
            try:
                import paramiko
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(host, username=user, password=password, timeout=15)
                sftp = client.open_sftp()
                local_path = os.path.join(os.path.dirname(__file__), "..", "backend", "app", "routers", "auth.py")
                local_path = os.path.abspath(local_path)
                if os.path.isfile(local_path):
                    sftp.put(local_path, "/home/upbit/upbitAUTObot/backend/app/routers/auth.py")
                    report.append(("4b. auth.py SCP 업로드", "OK", "로컬->Jetson"))
                else:
                    report.append(("4b. auth.py SCP", "스킵", "로컬파일 없음"))
                sftp.close()
                client.close()
            except Exception as e:
                report.append(("4b. auth.py SCP", "실패", str(e)[:80]))

    # 5. systemctl 재시작 (먼저 비밀없이 시도, 실패 시 get_pty로 sudo 비밀번호 전달)
    code, out, err = run_ssh("sudo -n systemctl restart upbit-backend 2>/dev/null; echo EXIT=$?", password, host, user)
    if code != 0 or "EXIT=0" not in out:
        code, out, err = run_ssh("sudo systemctl restart upbit-backend", password, host, user, wait_sudo=True)
    run_ssh("sleep 6", password, host, user)
    code2, out2, _ = run_ssh("systemctl is-active upbit-backend 2>/dev/null || true", password, host, user)
    active = "active" in out2
    report.append(("5. upbit-backend 재시작", "active" if active else "비활성", out2.strip()))

    # 5b. pull 후 재확인: auth.py에 라우트 있는지
    code, out, _ = run_ssh(
        "grep -q 'send-verification-email' /home/upbit/upbitAUTObot/backend/app/routers/auth.py 2>/dev/null && echo HAS || echo NO",
        password, host, user
    )
    report.append(("5b. pull 후 인증메일 라우트", "OK" if "HAS" in out else "NO(저장소 미반영)", out.strip()))

    # 6. health
    code, out, err = run_ssh("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health", password, host, user)
    health_ok = out.strip() == "200"
    report.append(("6. GET /health", "200" if health_ok else out.strip() or "실패", ""))

    # 7. send-verification-email 노출
    code, out, err = run_ssh(
        "curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:8000/api/v1/auth/send-verification-email -H 'Content-Type: application/json' -d '{\"email\":\"t@e.com\"}'",
        password, host, user
    )
    api_code = out.strip()
    api_ok = api_code in ("200", "503", "400")  # 200 성공, 503 SMTP미설정, 400 이미가입
    report.append(("7. POST send-verification-email", api_code if api_code else "연결실패", "404면 구버전" if api_code == "404" else ""))

    # 8. openapi에 경로 있는지
    code, out, err = run_ssh(
        "curl -s http://127.0.0.1:8000/openapi.json | grep -o 'send-verification-email' | head -1",
        password, host, user
    )
    report.append(("8. OpenAPI 경로 노출", "OK" if "send-verification-email" in out else "없음", out.strip()))

    # 9. 서비스 실패 시 로그 (health/API 실패할 때만)
    if not health_ok or not api_ok:
        code, out, err = run_ssh(
            "sudo -n journalctl -u upbit-backend -n 30 --no-pager 2>/dev/null || true",
            password, host, user
        )
        if not out.strip():
            code, out, err = run_ssh("journalctl -u upbit-backend -n 30 --no-pager 2>/dev/null || true", password, host, user)
        report.append(("9. journalctl(최근)", "참고" if out.strip() else "-", (out.strip() or err.strip())[:500]))

    # 결과 출력
    print("\n=== Jetson 전 항목 점검·조치 결과 ===\n")
    for name, status, detail in report:
        print(f"  {name}: {status}")
        if detail:
            print(f"    -> {detail[:200]}")
    print()
    if not api_ok and api_code == "404":
        print("  [조치] 인증메일 API가 404입니다. auth.py SCP 업로드 후 재시작. PC에서 저장소 푸시 후 Jetson에서 git pull 권장.")
    if not health_ok or (not api_ok and api_code != "404"):
        print("  [참고] health/API 연결 실패(000) 시 서비스 재시작 중이거나 크래시 루프일 수 있음. Jetson에서 sudo journalctl -u upbit-backend -n 50 확인.")
    # 결과를 파일로 저장 (UTF-8)
    report_path = os.path.join(os.path.dirname(__file__), "..", "docs", "Jetson_점검_결과_최근.txt")
    report_path = os.path.abspath(report_path)
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("Jetson 전 항목 점검 결과\n\n")
            for name, status, detail in report:
                f.write(f"  {name}: {status}\n")
                if detail:
                    f.write(f"    -> {detail}\n")
    except Exception:
        pass
    print("\n=== 끝 ===\n")

if __name__ == "__main__":
    main()
