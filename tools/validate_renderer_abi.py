#!/usr/bin/env python3
"""Verify the linked ARM renderer bridges retain their reviewed stack shapes."""

import argparse
from pathlib import Path
import re
import shutil
import subprocess


OBJECTS = {
    "Gfx.s.o": {
        "gfxRefresh": (r"(?:push|stmfd\s+sp!,)\s*\{lr\}",
                       r"bl\s+.*<gfxEndFrame>"),
        "gfxRebuildRendererState": (
            "push\t{r4, r5, r6, r7, r8, r9, sl, lr}",
            "push\t{ip, lr}",
        ),
        "gfxEndFrame": (
            "push\t{r4, r5, r6, r7, r8, r9, lr}",
            "push\t{ip, lr}",
        ),
    },
    "Memory.s.o": {
        "cpuWriteWordUnaligned": ("push\t{r2, lr}", "pop\t{r2, lr}"),
        "paletteRamWriteNotify": (
            "push\t{r0, r1, r2, lr}",
            "pop\t{r0, r1, r2, pc}",
        ),
    },
    "Sphinx/WSVideo.s.o": {
        "wsvWrite16": (
            "push\t{r0, r1, ip, lr}",
            "pop\t{r0, r1, ip, lr}",
        ),
        "wsvBgColorW": (
            "push\t{r0, r1, r2, r3, ip, lr}",
            "pop\t{r0, r1, r2, r3, ip, pc}",
        ),
    },
}


def find_objdump(explicit: str | None) -> str:
    if explicit:
        return explicit
    found = shutil.which("arm-none-eabi-objdump")
    if found:
        return found
    raise SystemExit("arm-none-eabi-objdump not found; pass --objdump")


def function_body(disassembly: str, symbol: str) -> str:
    match = re.search(
        rf"^[0-9a-f]+ <{re.escape(symbol)}>:\n(.*?)(?=^[0-9a-f]+ <|\Z)",
        disassembly,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise AssertionError(f"missing symbol: {symbol}")
    return match.group(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--objdump")
    args = parser.parse_args()
    objdump = find_objdump(args.objdump)

    checked = 0
    for relative, functions in OBJECTS.items():
        path = args.build_dir / "source" / relative
        if not path.is_file():
            raise AssertionError(f"missing object: {path}")
        output = subprocess.run(
            [objdump, "-d", str(path)], check=True, capture_output=True,
            text=True,
        ).stdout
        for symbol, patterns in functions.items():
            body = function_body(output, symbol)
            for pattern in patterns:
                if re.search(pattern, body) is None:
                    raise AssertionError(f"{symbol}: missing {pattern!r}")
            checked += 1

    # Reviewed stack contracts, expressed as pushed 32-bit word counts.
    # The result is SP mod 8 immediately before each C BL/BLX.
    paths = {
        "frame-complete": (9, 1, 1, 7, 2),
        "new-frame": (9, 1, 2),
        "palette-byte-write": (9, 1, 4),
        "palette-unaligned-word-write": (9, 1, 2, 4),
        "video-byte-register-write": (9, 1, 6),
        "video-word-register-write": (9, 1, 4, 6),
        "direct-video-word-register-write": (4, 6),
        "direct-gfx-refresh": (1, 7, 2),
        "restore-rebuild": (8, 2),
        "host-vblank": (4,),
    }
    for name, pushes in paths.items():
        mod8 = (-4 * sum(pushes)) % 8
        if mod8 != 0:
            raise AssertionError(f"{name}: SP is {mod8} mod 8 before C call")
    print(f"PASS renderer ABI: {checked} linked symbols, {len(paths)} call paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
