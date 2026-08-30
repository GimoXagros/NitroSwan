# WonderSwan ROM fetch wait-state timing vector

Status: **hardware verification pending**. No value in this document is presented as a real-hardware measurement.

## Hardware bit definition

System Control port `$A0` uses bit 2 for cartridge ROM bus width and bit 3 for cartridge ROM wait state:

- bit 2: `0` = 8-bit ROM, `1` = 16-bit ROM
- bit 3: `0` = +0 cycles, `1` = +1 cartridge-bus cycle

This agrees with WSdev's System Control documentation and with the existing NitroSwan GDMA check. The test holds bit 2 at `1` and toggles only bit 3.

## What the ROM measures

Each row is run twice with the same code and data:

- `W0`: `$A0` bit 3 clear
- `W1`: `$A0` bit 3 set
- `DELTA`: `W1 - W0`

Values are elapsed HBlank scanlines in hexadecimal. The HBlank timer has scanline resolution, so a one-line variation between runs is normal.

The rows cover:

- `RAM NOP`, `RAM ALU`, `RAM BR`: code copied to and executed from internal RAM
- `ROM NOP`, `ROM ALU`: sequential one-byte/two-byte instruction streams
- `ROM IMM`, `MODRM+IM`: instruction-stream immediate, ModR/M and displacement bytes
- `BR TAKE`, `JMP NEAR`, `BR NOT`, `CALL RET`: control-flow and prefetch-flush cases
- `BYTE SEQ`, `WORD SEQ`, `BYTE RND`: cartridge ROM data reads; these distinguish hardware data timing from NitroSwan's requested opcode-only implementation scope

The required vector relationship is:

- Vector A: internal RAM execution (`RAM *`, W0/W1)
- Vector B: cartridge ROM execution with wait state off (`ROM *`, W0)
- Vector C: cartridge ROM execution with wait state on (`ROM *`, W1)

Hardware evidence is the measured `C - B` relationship. Do not copy emulator output into the hardware-result section.

## Build

Requirements:

- Python 3
- NASM with 80186 support

Windows PowerShell:

```powershell
./build.ps1
```

Unix-like shell:

```sh
./build.sh
```

The output is `rom_fetch_waitstate.ws`, a 1 MiB monochrome-compatible WonderSwan test ROM with a patched 16-bit checksum. The executable is placed in the final 64 KiB bank so the physical mapping and ROM-size header agree.

## Real-hardware procedure

1. Flash `rom_fetch_waitstate.ws` to a cartridge known to run homebrew on the target WonderSwan or WonderSwan Color.
2. Cold boot the console. Do not resume from a savestate.
3. Wait until all result rows appear.
4. Photograph the entire screen or transcribe every `W0`, `W1`, and `DELTA` value.
5. Power-cycle and repeat at least three times.
6. Report the console model and flash cartridge/loader.

Use this exact reply format:

```text
Console: WonderSwan / WonderSwan Color / SwanCrystal
Cartridge/loader:
Run 1:
CONTROL  W0=____ W1=____ D=____
RAM NOP  W0=____ W1=____ D=____
RAM ALU  W0=____ W1=____ D=____
RAM BR   W0=____ W1=____ D=____
ROM NOP  W0=____ W1=____ D=____
ROM ALU  W0=____ W1=____ D=____
ROM IMM  W0=____ W1=____ D=____
BR TAKE  W0=____ W1=____ D=____
JMP NEAR W0=____ W1=____ D=____
BR NOT   W0=____ W1=____ D=____
CALL RET W0=____ W1=____ D=____
BYTE SEQ W0=____ W1=____ D=____
WORD SEQ W0=____ W1=____ D=____
BYTE RND W0=____ W1=____ D=____
MODRM+IM W0=____ W1=____ D=____
Run 2: ...
Run 3: ...
```

## Emulator results

Keep emulator output separate from real-hardware output:

```text
Emulator/build:
Commit:
Results:
```

Until a real console has produced repeatable values, the opcode-fetch implementation remains a test candidate and must not be described as hardware-verified.
