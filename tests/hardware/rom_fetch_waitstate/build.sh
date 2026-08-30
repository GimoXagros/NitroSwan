#!/usr/bin/env sh
set -eu

test_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 "$test_dir/generate_font.py"
cd "$test_dir"
nasm -f bin -Wall -w-reloc-abs-word -o rom_fetch_waitstate.ws rom_fetch_waitstate.asm
python3 "$test_dir/fix_checksum.py" "$test_dir/rom_fetch_waitstate.ws"
sha256sum "$test_dir/rom_fetch_waitstate.ws"
