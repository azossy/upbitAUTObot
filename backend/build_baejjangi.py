#!/usr/bin/env python3
"""
baejjangi CLI 단일 실행 파일 빌드 (PyInstaller).
실행: pip install pyinstaller && python build_baejjangi.py
결과: dist/baejjangi (Linux/Jetson/macOS) 또는 dist/baejjangi.exe (Windows)
사용: ./baejjangi 또는 baejjangi → 사용법 안내
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent


def main() -> int:
    try:
        import PyInstaller.__main__  # noqa: F401
    except ImportError:
        print("PyInstaller가 필요합니다: pip install pyinstaller")
        return 1

    # backend를 path로 주어 app 패키지를 찾고, 단일 실행 파일로 뱉음
    args = [
        str(BACKEND / "baejjangi.py"),
        "--name=baejjangi",
        "--onefile",
        f"--paths={BACKEND}",
        "--hidden-import=pydantic_settings",
        "--hidden-import=app.config",
        "--hidden-import=app.services.email_service",
        "--hidden-import=httpx",
        "--noconfirm",
        "--clean",
    ]

    print("빌드 중: PyInstaller --onefile baejjangi ...")
    return subprocess.call([sys.executable, "-m", "PyInstaller"] + args, cwd=str(BACKEND))


if __name__ == "__main__":
    sys.exit(main() or 0)
