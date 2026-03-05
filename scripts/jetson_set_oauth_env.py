#!/usr/bin/env python3
"""
Jetson 서버에 구글/카카오 OAuth용 환경 변수 적용 후 서비스 재시작.
구글·카카오 계정 회원가입 테스트를 위해 서버 .env에 GOOGLE_CLIENT_ID, KAKAO_REST_API_KEY를 넣습니다.

사용법 (프로젝트 루트에서):
  # 비밀번호만 입력 (값은 빈 문자열로 추가 → 앱에서 OAuth 시 503 안내)
  python scripts/jetson_set_oauth_env.py

  # 키를 이미 발급받았다면 환경 변수로 전달
  set GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com
  set KAKAO_REST_API_KEY=xxxxxxxx
  python scripts/jetson_set_oauth_env.py

  # 또는 한 줄 (PowerShell)
  $env:GOOGLE_CLIENT_ID="xxxx"; $env:KAKAO_REST_API_KEY="yyyy"; python scripts/jetson_set_oauth_env.py
"""
import os
import sys
import re

def run_ssh(cmd: str, password: str, host: str, user: str, wait_sudo: bool = False) -> tuple:
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


def sftp_get_env(password: str, host: str, user: str, remote_path: str):
    """Jetson .env 파일 내용 읽기 (SFTP)."""
    try:
        import paramiko
    except ImportError:
        return False, ""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=user, password=password, timeout=15)
        sftp = client.open_sftp()
        try:
            with sftp.file(remote_path, "r") as f:
                return True, f.read().decode("utf-8", errors="replace")
        except FileNotFoundError:
            return True, ""
        finally:
            sftp.close()
    except Exception as e:
        return False, str(e)
    finally:
        client.close()


def sftp_put_env(password: str, host: str, user: str, remote_path: str, content: str):
    """Jetson .env 파일 쓰기 (SFTP)."""
    try:
        import paramiko
    except ImportError:
        return False, "paramiko 미설치"
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=user, password=password, timeout=15)
        sftp = client.open_sftp()
        try:
            with sftp.file(remote_path, "w") as f:
                f.write(content.encode("utf-8"))
            return True, ""
        except Exception as e:
            return False, str(e)
        finally:
            sftp.close()
    except Exception as e:
        return False, str(e)
    finally:
        client.close()


def main():
    password = os.environ.get("JETSON_SSH_PASSWORD", "").strip()
    if not password:
        import getpass
        password = getpass.getpass("Jetson SSH 비밀번호: ")

    host = "100.80.178.45"
    user = "upbit"
    remote_env = "/home/upbit/baejjangi/backend/.env"

    google_id = (os.environ.get("GOOGLE_CLIENT_ID") or "").strip()
    kakao_key = (os.environ.get("KAKAO_REST_API_KEY") or "").strip()

    print("=== Jetson 구글/카카오 OAuth 환경 변수 적용 ===\n")
    print("  GOOGLE_CLIENT_ID: ", "설정됨" if google_id else "(비어 있음 → 앱에서 구글 로그인 시 503 안내)")
    print("  KAKAO_REST_API_KEY:", "설정됨" if kakao_key else "(비어 있음 → 앱에서 카카오 로그인 시 503 안내)")
    print()

    # 1. 현재 .env 읽기
    print("[1/4] Jetson .env 읽는 중 ...")
    ok, body = sftp_get_env(password, host, user, remote_env)
    if not ok:
        # SFTP 실패 시 cat으로 시도
        code, out, err = run_ssh(f"cat {remote_env} 2>/dev/null || true", password, host, user)
        body = out if code == 0 else ""
    lines = [ln.rstrip("\r\n") for ln in body.split("\n")] if body else []

    # 2. 기존 OAuth 행 제거 후 새 값으로 추가
    def drop_key(ln: str, key: str) -> bool:
        return ln.strip().startswith(key + "=")
    lines = [ln for ln in lines if not drop_key(ln, "GOOGLE_CLIENT_ID") and not drop_key(ln, "KAKAO_REST_API_KEY")]
    # 끝에 빈 줄 제거 후 OAuth 변수 추가
    while lines and lines[-1].strip() == "":
        lines.pop()
    if lines and lines[-1].strip() != "":
        lines.append("")
    lines.append("# 구글/카카오 로그인 (jetson_set_oauth_env.py)")
    lines.append(f"GOOGLE_CLIENT_ID={google_id}")
    lines.append(f"KAKAO_REST_API_KEY={kakao_key}")
    new_content = "\n".join(lines) + "\n"

    # 3. .env 쓰기
    print("[2/4] .env에 OAuth 변수 쓰는 중 ...")
    ok, err = sftp_put_env(password, host, user, remote_env, new_content)
    if not ok:
        print("  실패:", err)
        sys.exit(1)
    print("  OK")

    # 4. 서비스 재시작
    print("\n[3/4] systemctl restart baejjangi-backend ...")
    code, out, err = run_ssh("sudo -n systemctl restart baejjangi-backend 2>/dev/null; echo EXIT=$?", password, host, user)
    if "EXIT=0" not in (out or ""):
        code, out, err = run_ssh("sudo systemctl restart baejjangi-backend", password, host, user, wait_sudo=True)
    if code != 0:
        print("  실패:", (out or err).strip()[:200])
        sys.exit(1)
    print("  OK")
    import time
    time.sleep(5)

    # 5. health
    print("\n[4/4] health 확인 ...")
    code, out, _ = run_ssh("curl -s http://127.0.0.1:8000/health", password, host, user)
    if code == 0 and out and "ok" in out.lower():
        print("  정상:", out.strip()[:120])
        print("\n" + "=" * 50)
        print("  Jetson OAuth 환경 변수 적용 및 서버 재시작 완료.")
        if not google_id or not kakao_key:
            print("  구글/카카오 키가 비어 있으면 앱에서 해당 로그인 시 503 안내가 나옵니다.")
            print("  키 발급 후 위 환경 변수로 다시 실행하거나, Jetson에서 .env를 직접 수정하세요.")
        print("=" * 50)
    else:
        print("  응답:", (out or "(없음)").strip()[:200])
        sys.exit(1)


if __name__ == "__main__":
    main()
