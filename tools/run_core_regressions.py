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
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])

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

        cache_exe = Path(temp_dir) / ("dspico_rom_cache_test.exe" if os.name == "nt" else "dspico_rom_cache_test")
        run([
            compiler,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-Isource",
            "tests/test_dspico_rom_cache.c",
            "source/DspicoRomCache.c",
            "-o",
            str(cache_exe),
        ])
        run([str(cache_exe)])

    else:
        print("Host C compiler unavailable; C vectors will run in CI, Python vectors passed locally.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
