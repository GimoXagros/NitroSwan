#!/usr/bin/env python3
"""Validate release NDS headers, executable ranges and the static icon/banner."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def crc16(data):
    crc = 0xFFFF
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = (crc >> 1) ^ (0xA001 if crc & 1 else 0)
    return crc


def check(path, dsi):
    data = path.read_bytes()
    assert len(data) >= 0x200, f"{path}: truncated header"
    unit = data[0x12]
    assert (unit in (2, 3)) if dsi else (unit == 0), (path, unit)
    assert crc16(data[:0x15E]) == struct.unpack_from("<H", data, 0x15E)[0], "header CRC"
    for name, offset in (("ARM9", 0x20), ("ARM7", 0x30)):
        rom, entry, ram, size = struct.unpack_from("<IIII", data, offset)
        assert size > 0 and rom >= 0x200 and rom + size <= len(data), (name, rom, size)
    banner = struct.unpack_from("<I", data, 0x68)[0]
    assert banner >= 0x200 and banner + 0x840 <= len(data), "missing banner"
    raw = data[banner:banner + 0x840]
    assert struct.unpack_from("<H", raw)[0] in (1, 2, 3, 0x103), "banner version"
    assert crc16(raw[0x20:0x840]) == struct.unpack_from("<H", raw, 2)[0], "banner CRC"
    assert any(raw[0x20:0x220]) and any(raw[0x220:0x240]), "empty icon/palette"
    titles = []
    for i in range(6):
        title = raw[0x240 + i * 0x100:0x340 + i * 0x100].decode("utf-16le").split("\0")[0]
        assert "NitroSwan" in title, (i, title)
        titles.append(title)
    return {"file": path.name, "bytes": len(data), "unitCode": unit,
            "sha256": hashlib.sha256(data).hexdigest(), "banner_titles": titles}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ds", type=Path, required=True)
    parser.add_argument("--dsi", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps([check(args.ds, False), check(args.dsi, True)], indent=2))
