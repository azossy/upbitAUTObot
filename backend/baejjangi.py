#!/usr/bin/env python3
"""
배짱이 v1.1 — 운영용 CLI
설정(텔레그램·이메일 등)을 문답식으로 변경 후 backend/.env에 반영.
메일/텔레그램/카카오 설정 테스트: baejjangi test (mail|telegram|kakao)
실행: baejjangi [--help] | baejjangi set (telegram|email) | baejjangi test (mail|telegram|kakao)
      컴파일 후: ./baejjangi 또는 baejjangi.exe
리눅스: --stop, --restart, --status (systemd baejjangi-backend), --user (앱 사용자 목록+최근 접속일)
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import subprocess
import sys
from pathlib import Path

# PyInstaller onefile 시 실행 파일 기준 디렉터리 사용
if getattr(sys, "frozen", False):
    _BACKEND_DIR = Path(sys.executable).resolve().parent
else:
    _BACKEND_DIR = Path(__file__).resolve().parent

# backend 디렉터리를 path에 넣어 app 임포트 가능하게 (프로젝트 루트에서 실행해도 동작)
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# 기본 .env 경로: 실행 파일/스크립트와 같은 디렉터리
DEFAULT_ENV = _BACKEND_DIR / ".env"

BAEJJANGI_VERSION = "1.4.5"


def parse_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1].replace('\\"', '"')
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1].replace("\\'", "'")
            out[key] = val
    return out


def write_env(path: Path, data: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# 배짱이 v1.1 — 환경 변수 (baejjangi CLI로 수정)", ""]
    for k, v in data.items():
        if "\n" in v or '"' in v or " " in v:
            v_esc = v.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{k}="{v_esc}"')
        else:
            lines.append(f"{k}={v}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def prompt(text: str, default: str | None = None) -> str:
    msg = f"{text} ({default}) " if default else f"{text} "
    try:
        line = input(msg).strip()
    except EOFError:
        return default or ""
    return line if line else (default or "")


def cmd_set_telegram(env_path: Path) -> None:
    data = parse_env(env_path)
    print("--- 텔레그램 알림 설정 ---")
    data["TELEGRAM_BOT_TOKEN"] = prompt("TELEGRAM_BOT_TOKEN", data.get("TELEGRAM_BOT_TOKEN", ""))
    data["TELEGRAM_DEFAULT_CHAT_ID"] = prompt("TELEGRAM_DEFAULT_CHAT_ID", data.get("TELEGRAM_DEFAULT_CHAT_ID", ""))
    write_env(env_path, data)
    print(f".env 반영됨: {env_path}")


def cmd_set_email(env_path: Path) -> None:
    data = parse_env(env_path)
    print("--- 이메일(SMTP) 설정 ---")
    data["SMTP_HOST"] = prompt("SMTP_HOST", data.get("SMTP_HOST", "smtp.gmail.com"))
    data["SMTP_PORT"] = prompt("SMTP_PORT", str(data.get("SMTP_PORT", "587")))
    data["SMTP_USER"] = prompt("SMTP_USER", data.get("SMTP_USER", ""))
    data["SMTP_PASSWORD"] = prompt("SMTP_PASSWORD", data.get("SMTP_PASSWORD", ""))
    data["EMAIL_FROM"] = prompt("EMAIL_FROM", data.get("EMAIL_FROM", "배짱이 <noreply@example.com>"))
    data["VERIFICATION_CODE_EXPIRE_MINUTES"] = prompt(
        "VERIFICATION_CODE_EXPIRE_MINUTES",
        str(data.get("VERIFICATION_CODE_EXPIRE_MINUTES", "1")),
    )
    write_env(env_path, data)
    print(f".env 반영됨: {env_path}")


def _load_env_into_os(env_path: Path) -> None:
    """테스트 명령에서 사용: .env 값을 os.environ에 넣어 app.config가 읽도록."""
    for k, v in parse_env(env_path).items():
        os.environ.setdefault(k, v)
    # pydantic-settings는 env_file을 cwd 기준으로 찾을 수 있으므로, 명시적으로 지정된 경로 적용
    os.environ.setdefault("ENV_FILE", str(env_path))


def _send_test_email_from_env(env_path: Path, to: str) -> tuple[bool, str | None]:
    """.env의 SMTP 설정으로 테스트 메일 발송. (성공여부, 실패 시 오류 메시지) 반환."""
    import smtplib
    import ssl
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    data = parse_env(env_path)
    host = (data.get("SMTP_HOST") or "").strip()
    user = (data.get("SMTP_USER") or "").strip()
    password = (data.get("SMTP_PASSWORD") or "").strip()
    if not host or not user or not password:
        return False, "SMTP_HOST, SMTP_USER, SMTP_PASSWORD 중 누락"
    port = int(data.get("SMTP_PORT", "587") or "587")
    from_addr = (data.get("EMAIL_FROM") or "배짱이 <noreply@example.com>").strip()
    subject = "[배짱이] 메일 설정 테스트"
    contact = (data.get("APP_CONTACT_EMAIL") or "baejjangi@example.com").strip() or "baejjangi@example.com"
    try:
        from app.services.email_footer_constants import get_footer_plain
        footer = get_footer_plain(contact)
    except ImportError:
        footer = (
            "\n\n---\n"
            "배짱이 앱은 엄청난 연구와 실제 테스트를 거쳐 안정성 있게 만들어진, "
            "최고의 엔진이 탑재된 좋은 앱입니다.\n"
            "궁금한 점이 있으면 이메일을 보내 주세요: " + contact
        )
    body = "배짱이 CLI(baejjangi test mail)에서 발송한 테스트 메일입니다. 설정이 정상입니다." + footer
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to
        msg.attach(MIMEText(body, "plain", "utf-8"))
        ctx = ssl.create_default_context()
        with smtplib.SMTP(host, port) as server:
            if port == 587:
                server.starttls(context=ctx)
            server.login(user, password)
            server.sendmail(user, to, msg.as_string())
        return True, None
    except Exception as e:
        return False, str(e)


def cmd_test_mail(env_path: Path) -> int:
    """메일(SMTP) 설정 테스트: .env의 SMTP로 테스트 메일 1통 발송. app 패키지 없이 동작."""
    data = parse_env(env_path)
    if not (data.get("SMTP_HOST") and data.get("SMTP_USER") and data.get("SMTP_PASSWORD")):
        print("오류: SMTP가 설정되지 않았습니다. baejjangi set email 으로 설정 후 시도하세요.")
        return 1
    to = prompt("테스트 수신 이메일 주소", "").strip()
    if not to:
        print("수신 주소가 비어 있어 건너뜁니다.")
        return 0
    ok, err = _send_test_email_from_env(env_path, to)
    if ok:
        print(f"성공: {to} 로 테스트 메일을 발송했습니다. 메일함을 확인하세요.")
        return 0
    print("실패: 메일 발송에 실패했습니다. SMTP 호스트/포트/계정/비밀번호를 확인하세요.")
    if err:
        print(f"상세: {err}")
    return 1


def cmd_test_telegram(env_path: Path) -> int:
    """텔레그램 설정 테스트: .env의 봇 토큰·Chat ID로 테스트 메시지 1통 발송."""
    _load_env_into_os(env_path)
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_DEFAULT_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("오류: TELEGRAM_BOT_TOKEN 또는 TELEGRAM_DEFAULT_CHAT_ID가 비어 있습니다. baejjangi set telegram 으로 설정하세요.")
        return 1
    try:
        import httpx
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        with httpx.Client(timeout=10.0) as client:
            r = client.post(url, json={"chat_id": chat_id.strip(), "text": "배짱이 CLI 테스트 메시지입니다. 텔레그램 설정이 정상입니다."})
        if r.status_code == 200:
            print("성공: 텔레그램으로 테스트 메시지를 보냈습니다. 앱/채팅을 확인하세요.")
            return 0
        print(f"실패: API 응답 {r.status_code} - {r.text[:200]}")
        return 1
    except Exception as e:
        print(f"실패: {e}")
        return 1


def cmd_test_kakao(env_path: Path) -> int:
    """카카오(로그인) 설정 확인: KAKAO_REST_API_KEY가 설정되어 있는지 확인."""
    _load_env_into_os(env_path)
    key = os.environ.get("KAKAO_REST_API_KEY", "").strip()
    if not key:
        print("오류: KAKAO_REST_API_KEY가 비어 있습니다. 카카오 개발자 콘솔에서 REST API 키를 .env에 설정하세요.")
        return 1
    print("확인: KAKAO_REST_API_KEY가 설정되어 있습니다. (앱에서 카카오 로그인 사용 가능)")
    return 0


def _mask(value: str) -> str:
    """민감 정보 마스킹: 앞뒤 일부만 보여주고 중간은 ***."""
    if not value or len(value) <= 4:
        return "***" if value else "(비어 있음)"
    return value[:2] + "***" + value[-2:] if len(value) > 6 else "***"


def cmd_config(env_path: Path) -> int:
    """현재 .env 설정 요약 표시 (민감정보 마스킹)."""
    data = parse_env(env_path)
    if not data:
        print(f".env 파일이 없거나 비어 있습니다: {env_path}")
        return 0
    sensitive = {"SMTP_PASSWORD", "JWT_SECRET_KEY", "ENCRYPTION_KEY", "TELEGRAM_BOT_TOKEN"}
    print(f"--- .env 설정 요약 ({env_path}) ---")
    for k in sorted(data.keys()):
        v = data[k]
        if k in sensitive and v:
            v = _mask(v)
        elif len(v) > 60:
            v = v[:30] + "...(생략)"
        print(f"  {k}={v}")
    return 0


def cmd_health(base_url: str) -> int:
    """서버 /health 엔드포인트 체크."""
    try:
        import httpx
        url = base_url.rstrip("/") + "/health"
        with httpx.Client(timeout=5.0) as client:
            r = client.get(url)
        if r.status_code == 200:
            body = r.json()
            print(f"서버 정상: {body.get('status', 'ok')} (version: {body.get('version', '?')})")
            return 0
        print(f"실패: HTTP {r.status_code} - {r.text[:200]}")
        return 1
    except Exception as e:
        print(f"실패: {e}")
        return 1


SYSTEMD_SERVICE = "baejjangi-backend"
REPO_URL = "https://github.com/azossy/upbitAUTObot.git"
INSTALL_DIR_NAME = "baejjangi"


def _is_linux() -> bool:
    return sys.platform == "linux"


def _project_root() -> Path:
    """backend 디렉터리의 상위(프로젝트 루트, 예: ~/baejjangi)."""
    return _BACKEND_DIR.parent


def _run(cmd: list[str], cwd: Path | str | None = None, capture: bool = True) -> tuple[int, str]:
    """명령 실행. (exit_code, stdout+stderr)"""
    try:
        r = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture,
            text=True,
            timeout=120,
        )
        out = (r.stdout or "") + (r.stderr or "")
        return (r.returncode, out.strip())
    except subprocess.TimeoutExpired:
        return (-1, "타임아웃")
    except FileNotFoundError:
        return (-1, "명령을 찾을 수 없음")


def _run_sudo(cmd: list[str]) -> tuple[int, str]:
    """sudo 명령 실행."""
    return _run(["sudo"] + cmd, capture=True)


def cmd_update() -> int:
    """GitHub에서 최신 코드 pull, 의존성 설치, 서비스 재시작, health 검사. (.env 등 설정은 건드리지 않음)"""
    if not _is_linux():
        print("--update는 리눅스에서만 지원됩니다.")
        return 1
    root = _project_root()
    if not (root / ".git").exists():
        print(f"오류: Git 저장소가 아닙니다. {root}")
        return 1

    print("=== baejjangi --update ===\n")
    # 현재 버전
    ver_file = root / "VERSION"
    old_ver = ver_file.read_text().strip() if ver_file.exists() else "?"
    print(f"[1/5] 현재 버전: {old_ver}")

    # git pull
    code, out = _run(["git", "pull"], cwd=root)
    if code != 0:
        print(f"[2/5] git pull 실패: {out}")
        return 1
    print(f"[2/5] git pull: {out.split(chr(10))[0] if out else 'OK'}")

    # pip install
    venv_pip = _BACKEND_DIR / "venv" / "bin" / "pip"
    if venv_pip.exists():
        code2, out2 = _run([str(venv_pip), "install", "-q", "-r", "requirements.txt"], cwd=_BACKEND_DIR)
    else:
        code2, out2 = _run(["pip3", "install", "-q", "-r", "requirements.txt"], cwd=_BACKEND_DIR)
    if code2 != 0:
        print(f"[3/5] pip install 경고: {out2[:200]}")
    else:
        print("[3/5] pip install: OK")

    # 재시작
    code3, out3 = _run_sudo(["systemctl", "restart", SYSTEMD_SERVICE])
    if code3 != 0:
        print(f"[4/5] 서비스 재시작 실패: {out3}")
        return 1
    print("[4/5] 서비스 재시작: OK")
    import time
    time.sleep(4)

    # health
    code4, out4 = _run(["curl", "-s", "http://127.0.0.1:8000/health"], capture=True)
    new_ver = "?"
    if "version" in out4:
        try:
            import json
            new_ver = json.loads(out4).get("version", "?")
        except Exception:
            pass
    ok = code4 == 0 and "ok" in out4.lower()
    print(f"[5/5] health: {'정상' if ok else '실패'} (버전: {new_ver})")
    print("\n" + "=" * 50)
    print(f"  결과: {'업데이트 성공' if ok else '업데이트 후 확인 필요'}")
    print(f"  이전 버전: {old_ver}  →  현재: {new_ver}")
    print("=" * 50)
    return 0 if ok else 1


def cmd_reinstall() -> int:
    """기존 설치 제거 후 클론·설정 복원·venv·서비스 기동·테스트. (환경설정 .env/DB 는 백업 후 복원)"""
    if not _is_linux():
        print("--reinstall은 리눅스에서만 지원됩니다.")
        return 1

    import tempfile
    import shutil
    root = _project_root()
    parent = root.parent
    backup_dir = Path(tempfile.mkdtemp(prefix="baejjangi_reinstall_"))
    backend = root / "backend"

    def _step(n: int, msg: str) -> None:
        print(f"\n[{n}] {msg}")

    print("=== baejjangi --reinstall (클린 설치) ===\n")

    # 1. 백업 .env, *.db
    _step(1, "백업 (.env, DB)")
    if (backend / ".env").exists():
        shutil.copy2(backend / ".env", backup_dir / ".env")
        print("  .env 백업됨")
    if list(backend.glob("*.db")):
        for f in backend.glob("*.db"):
            shutil.copy2(f, backup_dir / f.name)
            print(f"  {f.name} 백업됨")

    # 2. 서비스 중지
    _step(2, "서비스 중지")
    _run_sudo(["systemctl", "stop", SYSTEMD_SERVICE])
    _run_sudo(["systemctl", "stop", "upbit-backend"])
    print("  OK")

    # 3. 클론은 새 폴더에 한 뒤, 기존 폴더와 교체 (실행 중인 디렉터리 직접 삭제 불가)
    _step(3, "Git 클론 (최신 저장소 → baejjangi_new)")
    clone_name = "baejjangi_new"
    code, out = _run(["git", "clone", REPO_URL, clone_name], cwd=parent)
    if code != 0:
        print(f"  실패: {out}")
        shutil.rmtree(backup_dir, ignore_errors=True)
        return 1
    new_root = parent / clone_name
    new_backend = new_root / "backend"
    if not new_backend.exists():
        print("  오류: backend 폴더 없음")
        shutil.rmtree(backup_dir, ignore_errors=True)
        return 1
    print("  OK")

    # 4. 설정 복원 (baejjangi_new/backend 에 복원)
    _step(4, "설정 복원 (.env, DB)")
    if (backup_dir / ".env").exists():
        shutil.copy2(backup_dir / ".env", new_backend / ".env")
        print("  .env 복원됨")
    else:
        if (new_backend / ".env.example").exists():
            shutil.copy2(new_backend / ".env.example", new_backend / ".env")
            print("  .env 없음 → .env.example 복사 (수동 설정 필요)")
    for f in backup_dir.glob("*.db"):
        shutil.copy2(f, new_backend / f.name)
        print(f"  {f.name} 복원됨")
    shutil.rmtree(backup_dir, ignore_errors=True)

    # 6. venv + pip
    _step(6, "가상환경 및 의존성 설치")
    code6, out6 = _run(["python3", "-m", "venv", "venv"], cwd=new_backend)
    if code6 != 0:
        print(f"  venv 실패: {out6}")
        return 1
    pip = new_backend / "venv" / "bin" / "pip"
    code6b, out6b = _run([str(pip), "install", "-q", "-r", "requirements.txt"], cwd=new_backend)
    if code6b != 0:
        print(f"  pip 경고: {out6b[:150]}")
    print("  OK")

    # 7. systemd 유닛 파일명 통일 (새 경로는 아직 baejjangi_new → 8에서 교체 후 baejjangi 가 됨)
    _step(7, "systemd baejjangi-backend.service")
    old_unit = Path("/etc/systemd/system/upbit-backend.service")
    new_unit = Path("/etc/systemd/system/baejjangi-backend.service")
    if old_unit.exists():
        _run_sudo(["mv", str(old_unit), str(new_unit)])
    if new_unit.exists():
        _run_sudo(["sed", "-i", "s|upbitAUTObot/backend|baejjangi/backend|g", str(new_unit)])
    _run_sudo(["systemctl", "daemon-reload"])
    print("  OK")

    # 8. 기존 baejjangi 제거 후 새 버전으로 교체
    _step(8, "기존 설치 제거 및 새 버전으로 교체")
    # upbitAUTObot 은 삭제, baejjangi 는 이름만 변경(실행 중인 디렉터리이므로 삭제 불가)
    for name in ["upbitAUTObot"]:
        d = parent / name
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
            print(f"  삭제: {d}")
    if (parent / INSTALL_DIR_NAME).exists():
        _run(["mv", str(parent / INSTALL_DIR_NAME), str(parent / "baejjangi_old")], cwd=parent)
        print("  기존 baejjangi → baejjangi_old")
    code_mv, _ = _run(["mv", str(new_root), str(parent / INSTALL_DIR_NAME)], cwd=parent)
    if code_mv != 0:
        print("  교체 실패")
        return 1
    print("  baejjangi_new → baejjangi OK")

    # 9. 서비스 기동
    _step(9, "서비스 기동")
    code8, out8 = _run_sudo(["systemctl", "start", SYSTEMD_SERVICE])
    if code8 != 0:
        print(f"  실패: {out8}")
        return 1
    import time
    time.sleep(5)
    print("  OK")

    # 10. 서버 테스트 (health, 인증메일 엔드포인트, 로그인 엔드포인트)
    _step(10, "서버 테스트")
    base = "http://127.0.0.1:8000"
    health_code, health_out = _run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"{base}/health"])
    health_ok = health_code == 0 and health_out.strip() == "200"
    mail_code, mail_out = _run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-X", "POST", f"{base}/api/v1/auth/send-verification-email", "-H", "Content-Type: application/json", "-d", '{"email":"test@example.com"}'])
    mail_ok = mail_code == 0 and mail_out.strip() in ("200", "400", "503")
    login_code, login_out = _run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-X", "POST", f"{base}/api/v1/auth/login", "-H", "Content-Type: application/json", "-d", '{"email":"x@x.com","password":"x"}'])
    login_ok = login_code == 0 and login_out.strip() == "401"

    print("\n" + "=" * 50)
    print("  재설치 결과")
    print("=" * 50)
    print(f"  health (/)           : {'정상' if health_ok else '실패'}")
    print(f"  인증메일 API         : {'응답 있음' if mail_ok else '실패'}")
    print(f"  로그인 API (401)     : {'정상' if login_ok else '실패'}")
    print("=" * 50)
    ver = "?"
    if health_ok:
        _, body = _run(["curl", "-s", f"{base}/health"])
        try:
            import json
            ver = json.loads(body).get("version", "?")
        except Exception:
            pass
    print(f"  백엔드 버전: {ver}")
    print("=" * 50 + "\n")
    return 0 if health_ok else 1


def cmd_systemd_stop() -> int:
    """systemd baejjangi-backend 서비스 중지 (리눅스에서만)."""
    if not _is_linux():
        print("--stop은 리눅스에서만 지원됩니다.")
        return 1
    try:
        subprocess.run(
            ["systemctl", "stop", SYSTEMD_SERVICE],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"{SYSTEMD_SERVICE} 서비스를 중지했습니다.")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"실패: {e.stderr or str(e)}")
        return 1
    except FileNotFoundError:
        print("systemctl을 찾을 수 없습니다. 리눅스 환경인지 확인하세요.")
        return 1


def cmd_systemd_restart() -> int:
    """systemd baejjangi-backend 서비스 재시작 (리눅스에서만)."""
    if not _is_linux():
        print("--restart는 리눅스에서만 지원됩니다.")
        return 1
    try:
        subprocess.run(
            ["systemctl", "restart", SYSTEMD_SERVICE],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"{SYSTEMD_SERVICE} 서비스를 재시작했습니다.")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"실패: {e.stderr or str(e)}")
        return 1
    except FileNotFoundError:
        print("systemctl을 찾을 수 없습니다. 리눅스 환경인지 확인하세요.")
        return 1


def cmd_systemd_status() -> int:
    """systemd baejjangi-backend 서비스 상태 출력 (리눅스에서만)."""
    if not _is_linux():
        print("--status는 리눅스에서만 지원됩니다.")
        return 1
    try:
        r = subprocess.run(
            ["systemctl", "status", SYSTEMD_SERVICE],
            capture_output=True,
            text=True,
        )
        print(r.stdout or r.stderr or "")
        return 0 if r.returncode == 0 else 1
    except FileNotFoundError:
        print("systemctl을 찾을 수 없습니다. 리눅스 환경인지 확인하세요.")
        return 1


async def _cmd_user_async(env_path: Path) -> int:
    """앱 사용자 목록 + 최근 접속일 DB 조회 (비동기)."""
    _load_env_into_os(env_path)
    # DATABASE_URL이 상대 경로(./baejjangi.db)면 backend 디렉터리 기준으로 절대 경로로 설정
    db_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./baejjangi.db")
    if "sqlite" in db_url and ("/./baejjangi.db" in db_url or db_url.rstrip("/").endswith("/./baejjangi.db")):
        db_path = _BACKEND_DIR / "baejjangi.db"
        os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    try:
        from sqlalchemy import select
        from app.database import AsyncSessionLocal
        from app.models.user import User
    except ImportError as e:
        print(f"DB 조회에 필요한 모듈을 불러올 수 없습니다: {e}")
        return 1
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User.id, User.email, User.nickname, User.last_login_at).order_by(User.id)
            )
            rows = result.all()
    except Exception as e:
        print(f"DB 조회 실패: {e}")
        return 1
    if not rows:
        print("등록된 사용자가 없습니다.")
        return 0
    # 표 형태로 출력 (id, email, nickname, last_login_at)
    col_id = "id"
    col_email = "email"
    col_nickname = "nickname"
    col_last = "last_login_at"
    lens = [len(col_id), len(col_email), len(col_nickname), len(col_last)]
    for r in rows:
        uid, email, nickname, last_at = r
        last_str = last_at.strftime("%Y-%m-%d %H:%M") if last_at else "(없음)"
        lens[0] = max(lens[0], len(str(uid)))
        lens[1] = max(lens[1], len(email or ""))
        lens[2] = max(lens[2], len(nickname or ""))
        lens[3] = max(lens[3], len(last_str))
    fmt = f"{{:<{lens[0]}}}  {{:<{lens[1]}}}  {{:<{lens[2]}}}  {{:<{lens[3]}}}"
    print(fmt.format(col_id, col_email, col_nickname, col_last))
    print("-" * (sum(lens) + 6))
    for r in rows:
        uid, email, nickname, last_at = r
        last_str = last_at.strftime("%Y-%m-%d %H:%M") if last_at else "(없음)"
        print(fmt.format(uid, email or "", nickname or "", last_str))
    return 0


def cmd_user(env_path: Path) -> int:
    """앱 사용자 목록 + 최근 접속일 출력."""
    return asyncio.run(_cmd_user_async(env_path))


def main() -> int:
    # 옵션 없이 실행 시 안내만 출력
    if len(sys.argv) == 1:
        print("사용법: baejjangi --help 를 입력하세요")
        return 0

    parser = argparse.ArgumentParser(
        prog="baejjangi",
        description="배짱이 v1.1 운영용 CLI. 설정(텔레그램/이메일 등) 변경 및 메일·텔레그램·카카오 테스트.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  baejjangi                    사용법 안내 (baejjangi --help 를 입력하세요)
  baejjangi --help
  baejjangi --version          버전 표시
  baejjangi config             .env 설정 요약 (민감정보 마스킹)
  baejjangi health [--url URL] 서버 /health 체크
  baejjangi set telegram       텔레그램 설정
  baejjangi set email          이메일(SMTP) 설정
  baejjangi test mail          메일 발송 테스트
  baejjangi test telegram      텔레그램 발송 테스트
  baejjangi test kakao         카카오 로그인 설정 확인
  baejjangi --stop             (리눅스) systemd baejjangi-backend 중지
  baejjangi --restart          (리눅스) systemd baejjangi-backend 재시작
  baejjangi --status           (리눅스) systemd baejjangi-backend 상태
  baejjangi --user             앱 사용자 목록 + 최근 접속일
  baejjangi --update           (리눅스) GitHub 최신 버전 pull·재시작·health 검사 (.env 유지)
  baejjangi --reinstall        (리눅스) 클린 재설치·설정 복원·서비스 기동·서버 테스트
  baejjangi --env-file /path/to/.env test mail
        """,
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV,
        help=f".env 파일 경로 (기본: {DEFAULT_ENV})",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="버전 표시",
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="(리눅스 전용) systemd baejjangi-backend 서비스 중지",
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="(리눅스 전용) systemd baejjangi-backend 서비스 재시작",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="(리눅스 전용) systemd baejjangi-backend 서비스 상태 출력",
    )
    parser.add_argument(
        "--user",
        action="store_true",
        help="앱 사용자 목록 + 최근 접속일 출력 (.env의 DB 사용)",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="(리눅스) GitHub에서 최신 코드 pull, pip 설치, 서비스 재시작, health 검사 (환경설정 .env 미변경)",
    )
    parser.add_argument(
        "--reinstall",
        action="store_true",
        help="(리눅스) 클린 재설치: 기존 제거 후 클론·설정 복원·venv·서비스 기동·서버 테스트",
    )
    sub = parser.add_subparsers(dest="command", title="서브커맨드")

    set_p = sub.add_parser("set", help="설정 항목을 문답식으로 입력받아 .env에 반영")
    set_sub = set_p.add_subparsers(dest="set_what", title="설정 항목")

    tg = set_sub.add_parser(
        "telegram",
        help="텔레그램 봇 토큰·기본 Chat ID 설정",
        description="TELEGRAM_BOT_TOKEN, TELEGRAM_DEFAULT_CHAT_ID 입력 후 .env 반영.",
    )
    tg.set_defaults(func=lambda a: cmd_set_telegram(a.env_file))

    em = set_sub.add_parser(
        "email",
        help="SMTP·발신자·인증 유효분 설정",
        description="SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM, VERIFICATION_CODE_EXPIRE_MINUTES 입력 후 .env 반영.",
    )
    em.set_defaults(func=lambda a: cmd_set_email(a.env_file))

    test_p = sub.add_parser("test", help="메일·텔레그램·카카오 설정 테스트 (Jetson 등 서버에서 동작 확인)")
    test_sub = test_p.add_subparsers(dest="test_what", title="테스트 항목")
    test_mail = test_sub.add_parser("mail", help="SMTP 설정 테스트: 테스트 메일 1통 발송")
    test_mail.set_defaults(func=lambda a: cmd_test_mail(a.env_file))
    test_telegram = test_sub.add_parser("telegram", help="텔레그램 설정 테스트: 테스트 메시지 1통 발송")
    test_telegram.set_defaults(func=lambda a: cmd_test_telegram(a.env_file))
    test_kakao = test_sub.add_parser("kakao", help="카카오 로그인 설정 확인 (KAKAO_REST_API_KEY)")
    test_kakao.set_defaults(func=lambda a: cmd_test_kakao(a.env_file))

    config_p = sub.add_parser("config", help="현재 .env 설정 요약 (민감정보 마스킹)")
    config_p.set_defaults(func=lambda a: cmd_config(a.env_file))

    health_p = sub.add_parser("health", help="서버 /health 엔드포인트 체크")
    health_p.add_argument(
        "--url",
        type=str,
        default="http://127.0.0.1:8000",
        help="API 서버 주소 (기본: http://127.0.0.1:8000)",
    )
    health_p.set_defaults(func=lambda a: cmd_health(a.url))

    args = parser.parse_args()

    if getattr(args, "version", False):
        print(f"baejjangi {BAEJJANGI_VERSION}")
        return 0
    if getattr(args, "stop", False):
        return cmd_systemd_stop()
    if getattr(args, "restart", False):
        return cmd_systemd_restart()
    if getattr(args, "status", False):
        return cmd_systemd_status()
    if getattr(args, "user", False):
        return cmd_user(args.env_file)
    if getattr(args, "update", False):
        return cmd_update()
    if getattr(args, "reinstall", False):
        return cmd_reinstall()

    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "set" and args.set_what is None:
        set_p.print_help()
        return 0
    if args.command == "test" and args.test_what is None:
        test_p.print_help()
        return 0

    if hasattr(args, "func") and args.func:
        out = args.func(args)
        return int(out) if isinstance(out, int) else 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
