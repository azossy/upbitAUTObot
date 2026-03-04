#!/usr/bin/env python3
"""
배짱이 v1.1 — 운영용 CLI
설정(텔레그램·이메일 등)을 문답식으로 변경 후 backend/.env에 반영.
실행: python baejjangi.py [--help] | python baejjangi.py set (telegram|email) [--help]
      또는 프로젝트 루트에서: python backend/baejjangi.py ...
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# 기본 .env 경로: 이 스크립트와 같은 디렉터리
DEFAULT_ENV = Path(__file__).resolve().parent / ".env"


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
        str(data.get("VERIFICATION_CODE_EXPIRE_MINUTES", "10")),
    )
    write_env(env_path, data)
    print(f".env 반영됨: {env_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="baejjangi",
        description="배짱이 v1.1 운영용 CLI. 텔레그램/이메일 등 설정을 문답식으로 변경 후 .env에 반영.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  baejjangi --help
  baejjangi set telegram
  baejjangi set email
  baejjangi --env-file /path/to/.env set telegram
        """,
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV,
        help=f".env 파일 경로 (기본: {DEFAULT_ENV})",
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

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "set" and args.set_what is None:
        set_p.print_help()
        return 0

    if hasattr(args, "func") and args.func:
        args.func(args)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
