#!/usr/bin/env python3
"""Build and run host-side core regressions plus source-level ARM checks."""

from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def find_c_compiler() -> str | None:
    candidates = [
        os.environ.get("CC"),
        shutil.which("cc"),
        shutil.which("gcc"),
        shutil.which("clang"),
        r"C:\Users\rlgh0\codex-build-tools\msys64\mingw64\bin\gcc.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    return None


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    run([sys.executable, "tests/test_rtc_calendar.py"])
    run([sys.executable, "tests/test_aswan_ram.py"])
    run([sys.executable, "tests/test_n3ds_cache.py"])
    run([sys.executable, "tests/test_settings_folder.py"])
    run([sys.executable, "tests/test_timing_core.py"])
    run([sys.executable, "tests/test_graphics_core.py"])
    run([sys.executable, "tests/test_sound_core.py"])
    run([sys.executable, "tests/test_speed_core.py"])

    compiler = find_c_compiler()
    if compiler:
      with tempfile.TemporaryDirectory(prefix="nitroswan-tests-") as temp_dir:
        exe = Path(temp_dir) / ("rtc_calendar_test.exe" if os.name == "nt" else "rtc_calendar_test")
        run([
            compiler,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-Isource/WSCart/WSRTC",
            "tests/test_rtc_calendar.c",
            "source/WSCart/WSRTC/WSRTCCalendar.c",
            "-o",
            str(exe),
        ])
        run([str(exe)])
    else:
        print("Host C compiler unavailable; C vectors will run in CI, Python vectors passed locally.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
