#!/usr/bin/env python3
"""
배짱이 v1.1 — 서버 설치 스크립트 (문답식)
프로젝트 루트에서 실행: python scripts/install.py
backend/.env 생성·갱신, venv·pip 설치, (선택) systemd 안내.
"""
from __future__ import annotations

import os
import re
import secrets
import subprocess
import sys
from pathlib import Path

# 프로젝트 루트 = 이 스크립트의 상위 디렉터리
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
ENV_PATH = BACKEND_DIR / ".env"
REQUIREMENTS = BACKEND_DIR / "requirements.txt"

# 마스킹할 키 (비밀·토큰)
MASK_KEYS = {"JWT_SECRET_KEY", "ENCRYPTION_KEY", "SMTP_PASSWORD", "TELEGRAM_BOT_TOKEN", "KAKAO_REST_API_KEY"}


def mask_value(key: str, value: str) -> str:
    if not value or key not in MASK_KEYS:
        return value
    if len(value) <= 4:
        return "****"
    return value[:2] + "****" + value[-2:] if len(value) > 4 else "****"


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
    lines = [
        "# 배짱이 v1.1 — 환경 변수 (install.py로 생성/수정)",
        "",
    ]
    for k, v in data.items():
        if "\n" in v or '"' in v or " " in v:
            v_esc = v.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{k}="{v_esc}"')
        else:
            lines.append(f"{k}={v}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def prompt(prompt_text: str, default: str | None = None) -> str:
    if default is not None:
        msg = f"{prompt_text} ({default}) " if default else f"{prompt_text} "
    else:
        msg = f"{prompt_text} "
    try:
        line = input(msg).strip()
    except EOFError:
        return default or ""
    return line if line else (default or "")


def prompt_bool(prompt_text: str, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    while True:
        s = prompt(f"{prompt_text} [{d}]", "").lower() or ("y" if default else "n")
        if s in ("y", "yes"):
            return True
        if s in ("n", "no"):
            return False


def collect_env() -> dict[str, str]:
    """문답식으로 모든 설정 수집."""
    data: dict[str, str] = {}

    print("\n--- 필수 보안 키 ---")
    jwt = prompt("JWT_SECRET_KEY (64자 hex, 비워두면 자동 생성)", "")
    if not jwt:
        jwt = secrets.token_hex(32)
        print(f"  → 생성됨: {jwt[:8]}...")
    data["JWT_SECRET_KEY"] = jwt

    enc = prompt("ENCRYPTION_KEY (64자 hex, 비워두면 자동 생성)", "")
    if not enc:
        enc = secrets.token_hex(32)
        print(f"  → 생성됨: {enc[:8]}...")
    data["ENCRYPTION_KEY"] = enc

    print("\n--- 서버 ---")
    data["CORS_ORIGINS"] = prompt(
        "CORS_ORIGINS (쉼표 구분)",
        "http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000",
    )
    data["DEBUG"] = "true" if prompt_bool("DEBUG (true=개발)", True) else "false"

    print("\n--- OAuth (없으면 비움) ---")
    data["GOOGLE_CLIENT_ID"] = prompt("GOOGLE_CLIENT_ID", "")
    data["KAKAO_REST_API_KEY"] = prompt("KAKAO_REST_API_KEY", "")

    print("\n--- 텔레그램 (없으면 비움) ---")
    data["TELEGRAM_BOT_TOKEN"] = prompt("TELEGRAM_BOT_TOKEN", "")
    data["TELEGRAM_DEFAULT_CHAT_ID"] = prompt("TELEGRAM_DEFAULT_CHAT_ID", "")

    print("\n--- FCM (없으면 비움) ---")
    data["GOOGLE_APPLICATION_CREDENTIALS"] = prompt("GOOGLE_APPLICATION_CREDENTIALS (서비스 계정 JSON 경로)", "")

    print("\n--- 이메일(SMTP) ---")
    data["SMTP_HOST"] = prompt("SMTP_HOST", "smtp.gmail.com")
    data["SMTP_PORT"] = prompt("SMTP_PORT", "587")
    data["SMTP_USER"] = prompt("SMTP_USER", "")
    data["SMTP_PASSWORD"] = prompt("SMTP_PASSWORD", "")
    data["EMAIL_FROM"] = prompt("EMAIL_FROM", "배짱이 <noreply@example.com>")
    data["VERIFICATION_CODE_EXPIRE_MINUTES"] = prompt("VERIFICATION_CODE_EXPIRE_MINUTES", "10")

    print("\n--- DB ---")
    data["DATABASE_URL"] = prompt(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./baejjangi.db",
    )

    return data


def show_current_summary(env: dict[str, str]) -> None:
    """기존 .env 요약 출력 (민감값 마스킹)."""
    print("\n--- 현재 .env 요약 (비밀·토큰은 마스킹) ---")
    order = [
        "JWT_SECRET_KEY", "ENCRYPTION_KEY", "CORS_ORIGINS", "DEBUG",
        "GOOGLE_CLIENT_ID", "KAKAO_REST_API_KEY",
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_DEFAULT_CHAT_ID",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "EMAIL_FROM", "VERIFICATION_CODE_EXPIRE_MINUTES",
        "DATABASE_URL",
    ]
    for k in order:
        if k in env:
            v = mask_value(k, env[k])
            print(f"  {k}={v[:60] + '...' if len(v) > 60 else v}")
    for k, v in env.items():
        if k not in order:
            print(f"  {k}={mask_value(k, v)[:60]}")
    print()


def run_venv_pip() -> bool:
    """backend에 venv 생성 및 pip install. 성공 여부 반환."""
    venv_dir = BACKEND_DIR / "venv"
    if not venv_dir.exists():
        print("venv 생성 중...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True, cwd=str(PROJECT_ROOT))
    if not REQUIREMENTS.exists():
        print(f"  requirements.txt 없음: {REQUIREMENTS}")
        return False
    pip = venv_dir / "Scripts" / "pip.exe" if os.name == "nt" else venv_dir / "bin" / "pip"
    if not pip.exists():
        pip = venv_dir / "bin" / "pip"
    print("pip install -r requirements.txt 실행 중...")
    subprocess.run([str(pip), "install", "-r", str(REQUIREMENTS)], check=True, cwd=str(BACKEND_DIR))
    return True


def main() -> None:
    print("배짱이 v1.1 — 서버 설치 스크립트")
    print(f"프로젝트 루트: {PROJECT_ROOT}")
    print(f"backend: {BACKEND_DIR}")

    env_exists = ENV_PATH.exists()
    current = parse_env(ENV_PATH) if env_exists else {}

    if env_exists and current:
        show_current_summary(current)
        print("기존 .env가 있습니다. 선택하세요:")
        print("  [U] 그대로 사용 — .env 유지, venv/pip만 진행")
        print("  [M] 새로 입력(수정) — 문답식으로 재입력 후 .env 갱신")
        while True:
            choice = prompt("U 또는 M", "U").strip().upper()
            if choice == "U":
                print(".env 유지. 다음 단계만 진행합니다.")
                run_venv_pip()
                break
            if choice == "M":
                current = collect_env()
                write_env(ENV_PATH, current)
                print(f".env 갱신됨: {ENV_PATH}")
                run_venv_pip()
                break
            print("U 또는 M 중 하나를 입력하세요.")
    else:
        data = collect_env()
        write_env(ENV_PATH, data)
        print(f".env 생성됨: {ENV_PATH}")
        run_venv_pip()

    print("\n--- 완료 ---")
    print("(선택) systemd로 상시 실행 시: docs/서버_설치_Jetson_Tailscale.md 4단계 참고.")
    print("서버 실행: cd backend && uvicorn main:app --host 0.0.0.0 --port 8000")
    print("확인: curl -s http://127.0.0.1:8000/health")


if __name__ == "__main__":
    main()
