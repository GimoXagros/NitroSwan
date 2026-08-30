#!/usr/bin/env python3
"""Verify that built NitroSwan NDS files contain the configured icon banner."""

from pathlib import Path
import struct
import sys


def verify(path: Path) -> None:
    data = path.read_bytes()
    if len(data) < 0x6C:
        raise ValueError("file is too small to contain an NDS header")

    banner_offset = struct.unpack_from("<I", data, 0x68)[0]
    banner_size = 0x840  # version 1 icon, palette and six UTF-16 titles
    if banner_offset == 0 or banner_offset + banner_size > len(data):
        raise ValueError("NDS banner is missing or truncated")

    version = struct.unpack_from("<H", data, banner_offset)[0]
    icon = data[banner_offset + 0x20 : banner_offset + 0x220]
    palette = data[banner_offset + 0x220 : banner_offset + 0x240]
    if version < 1 or not any(icon) or not any(palette):
        raise ValueError("NDS banner icon is empty")

    titles = []
    for language in range(6):
        start = banner_offset + 0x240 + language * 0x100
        raw = data[start : start + 0x100]
        title = raw.decode("utf-16le", errors="strict").split("\0", 1)[0]
        if not title:
            raise ValueError(f"NDS banner title {language} is empty")
        titles.append(title.replace("\n", " | "))

    print(f"{path}: banner v{version} at 0x{banner_offset:X}")
    print("titles: " + " || ".join(titles))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: verify_nds_banner.py FILE.nds [FILE.nds ...]")
    for argument in sys.argv[1:]:
        verify(Path(argument))
