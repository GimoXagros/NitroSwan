#!/usr/bin/env python3
"""Build and run host-side core regressions plus source-level ARM checks."""

from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def probe_host_compiler(compiler: str) -> bool:
    """Reject cross compilers and compilers whose output cannot run locally."""
    try:
        with tempfile.TemporaryDirectory(prefix="nitroswan-host-probe-") as temp:
            executable = Path(temp) / "probe.exe"
            subprocess.run(
                [compiler, str(ROOT / "tests/host_compiler_probe.c"),
                 "-o", str(executable)],
                cwd=ROOT, check=True, capture_output=True, timeout=30,
            )
            result = subprocess.run(
                [str(executable)], check=True, capture_output=True,
                text=True, timeout=10,
            )
            return result.stdout.strip() == "nitroswan-host-probe"
    except (OSError, subprocess.SubprocessError):
        return False


def find_c_compiler() -> str | None:
    # HOST_CC and CC are executable paths/names, not shell command strings.
    candidates = [os.environ.get("HOST_CC"), "cc", "gcc", "clang",
                  os.environ.get("CC")]
    seen = set()
    for candidate in candidates:
        if not candidate:
            continue
        resolved = shutil.which(candidate)
        if not resolved or resolved in seen:
            continue
        seen.add(resolved)
        if probe_host_compiler(resolved):
            return resolved
        print(f"SKIP compiler {Path(resolved).name}: host compile/run probe failed")
    return None


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])

    compiler = find_c_compiler()
    if compiler is None:
        print("SKIP host C regressions: no working host compiler; "
              "Python regressions passed. Set HOST_CC to a host C compiler.")
        # CI installs a host compiler; a missing one there must not look green.
        return 1 if os.environ.get("REQUIRE_HOST_CC") == "1" else 0

    with tempfile.TemporaryDirectory(prefix="nitroswan-tests-") as temp_dir:
        cases = (
            ("rtc_calendar", "source/WSCart/WSRTC",
             "source/WSCart/WSRTC/WSRTCCalendar.c"),
            ("dspico_rom_cache", "source", "source/DspicoRomCache.c"),
        )
        for name, include, source in cases:
            exe = Path(temp_dir) / f"{name}_test.exe"
            run([compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                 f"-I{include}", f"tests/test_{name}.c", source, "-o", str(exe)])
            run([str(exe)])
    print("PASS host C regressions: RTC calendar and DSpico ROM cache")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
