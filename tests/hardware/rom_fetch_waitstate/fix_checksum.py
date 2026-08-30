#!/usr/bin/env python3
"""Patch and verify the 16-bit WonderSwan ROM checksum."""

from pathlib import Path
import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rom", type=Path)
    args = parser.parse_args()

    data = bytearray(args.rom.read_bytes())
    if len(data) != 64 * 1024:
        raise SystemExit(f"expected a 65536-byte final-bank payload, got {len(data)}")

    # Header size $03 is a 1 MiB cartridge. Keep the assembled code in the last
    # bank (physical $F0000-$FFFFF) and fill the unused lower banks explicitly.
    data = bytearray(b"\xFF" * (15 * 64 * 1024)) + data

    data[-2:] = b"\x00\x00"
    checksum = sum(data[:-2]) & 0xFFFF
    data[-2:] = checksum.to_bytes(2, "little")
    args.rom.write_bytes(data)

    stored = int.from_bytes(data[-2:], "little")
    calculated = sum(data[:-2]) & 0xFFFF
    if stored != calculated:
        raise SystemExit("checksum verification failed")
    print(f"checksum=0x{stored:04X} size={len(data)}")


if __name__ == "__main__":
    main()
