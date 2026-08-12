#!/usr/bin/env python3
"""Validate embedded translations and their Galmuri-derived glyph coverage."""

from __future__ import annotations

import ast
import re
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCALIZATION = ROOT / "source" / "Localization.c"
FONT = ROOT / "assets" / "fonts" / "unicode_font.bin"
ENTRY = re.compile(
    r"\{\s*(\"(?:[^\"\\]|\\.)*\")\s*,\s*"
    r"(\"(?:[^\"\\]|\\.)*\")\s*,\s*"
    r"(\"(?:[^\"\\]|\\.)*\")\s*\}"
)


def c_string(value: str) -> str:
    return ast.literal_eval(value)


def load_font_codepoints() -> set[int]:
    data = FONT.read_bytes()
    if len(data) < 12 or data[:4] != b"GYUF":
        raise ValueError("invalid Unicode font magic")
    version, reserved, count = struct.unpack_from("<HHI", data, 4)
    if version != 1 or reserved != 0 or len(data) != 12 + count * 10:
        raise ValueError("invalid Unicode font structure")
    codepoints: set[int] = set()
    for offset in range(12, len(data), 10):
        codepoint = struct.unpack_from("<H", data, offset)[0]
        bitmap = data[offset + 2 : offset + 10]
        if codepoint in codepoints:
            raise ValueError(f"duplicate font codepoint U+{codepoint:04X}")
        if not any(bitmap):
            raise ValueError(f"empty font bitmap U+{codepoint:04X}")
        codepoints.add(codepoint)
    return codepoints


def main() -> None:
    source = LOCALIZATION.read_text(encoding="utf-8")
    table_start = source.index("static const LocalizedString strings[]")
    table_end = source.index("};", table_start)
    table_source = source[table_start:table_end]
    entries = [
        tuple(map(c_string, match.groups()))
        for match in ENTRY.finditer(table_source)
    ]
    if not entries:
        raise ValueError("no localization entries found")
    english_keys = [entry[0] for entry in entries]
    duplicates = sorted({key for key in english_keys if english_keys.count(key) > 1})
    if duplicates:
        raise ValueError(f"duplicate English localization keys: {duplicates}")

    font_codepoints = load_font_codepoints()
    missing: dict[str, set[int]] = {"Japanese": set(), "Korean": set()}
    for _, japanese, korean in entries:
        for language, text in (("Japanese", japanese), ("Korean", korean)):
            for character in text:
                codepoint = ord(character)
                if codepoint >= 0x80 and codepoint not in font_codepoints:
                    missing[language].add(codepoint)
    missing = {language: values for language, values in missing.items() if values}
    if missing:
        details = "; ".join(
            f"{language}: " + ", ".join(f"U+{value:04X}" for value in sorted(values))
            for language, values in missing.items()
        )
        raise ValueError(f"missing localized glyphs: {details}")

    print(
        f"OK: {len(entries)} entries; {len(font_codepoints)} non-ASCII glyphs; "
        "Japanese/Korean coverage complete"
    )


if __name__ == "__main__":
    main()
