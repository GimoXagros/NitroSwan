# Cartridge ROM instruction-stream wait state

Status: Mahjong Touryuumon is game-level verified on DSpico with normal speed,
sound and input. Standalone timing-vector capture on WonderSwan hardware is
still pending.

## Hardware definition

System Control port `$A0` uses bit 2 for cartridge ROM width and bit 3 for the
cartridge ROM wait state.  The latter adds one cartridge-bus cycle.  This is
also the interpretation already used by NitroSwan's general DMA guard in
`source/Sphinx/WSVideo.s`.

The corrected bit assignment matters because early task notes had the two bits
reversed.  Mahjong Touryuumon writes `0x0C`, so both bits are set and the trace
still proves that the game enables the ROM wait state.

## Existing paths

- Instruction bytes are read directly from `v30pc` by the macros in
  `source/ARMV30MZ/ARMV30MZmac.h`: the opcode, ModR/M, displacement and
  immediate-byte paths do not call `cpuReadMem20` for every byte.
- General byte/word data reads use `cpuReadMem20` and `cpuReadMem20W` in
  `source/Memory.s`.
- Physical segments `$2-$F` are cartridge ROM.  The cartridge mapper and the
  DSpico 64 KiB cache change the host pointer, not the emulated physical
  address.
- `wsvHWW` stores System Control `$A0`; the candidate also caches the wait-state
  flag there.  No Sphinx structure read or function call is added to the
  instruction-byte hot path.
- PC remapping calls a small classifier with both the emulated address and the
  mapped host pointer.  `$00000-$1FFFF`, plus an active boot-ROM overlay, are
  excluded.

The fetch-wait candidate does not add penalties to ordinary `Memory.s` data
reads/writes. Later r6/r7 work separately added palette-write notification there;
do not describe the whole file as unchanged from custom.r5. The `cpuWriteMem20`
r0/r1 preservation requirement still applies, including unaligned word writes.

## Upstream status (2026-09-03 snapshot)

[NitroSwan PR #60](https://github.com/FluBBaOfWard/NitroSwan/pull/60) remains
Open/Draft, head `de837923184219f075496928eda0bd2ded15cfad`. On 2026-08-30
the maintainer requested proper instruction prefetch rather than an instruction
byte penalty justified by one title. The 2026-08-31 reply accepted that request:
keep the candidate Draft, measure bus-width/refill/control-flow timing first,
then consider a low-cost generic implementation. Sphinx #5 and ARMV30MZ #6
are the separate dependency PRs. None is rewritten by the baseline audit.

The custom build's Mahjong DSpico result is a game-level improvement, NOT
validation of a native V30MZ prefetch/refill model. Native WonderSwan timing
vectors remain pending. See [BaselineAudit-r7.md](BaselineAudit-r7.md).

## Mahjong evidence

The user-supplied 1 MiB ROM has one direct immediate write to port `$A0`:

```text
file/physical $40069: B0 0C    mov al,$0C
file/physical $4006B: E6 A0    out $A0,al
```

The value enables 16-bit cartridge ROM width (bit 2) and the cartridge ROM
wait state (bit 3).  This is title-independent evidence; the implementation
does not inspect the ROM name, header or checksum.

## Candidate accounting

The cached active flag lives in the low, non-cycle bits of `v30cyc`.  Each
instruction-stream byte macro converts that flag to exactly `1*CYCLE` before
the byte is consumed.  The two ARM instructions used for the conversion do not
set ARM condition flags, because some V30 handlers fetch a byte between an ARM
comparison and a conditional operation.

This deliberately covers opcode, ModR/M, displacement and immediate bytes,
while leaving ordinary ROM data reads untouched.  It is a candidate model
until the hardware ROM in `tests/hardware/rom_fetch_waitstate` has been run on
real WonderSwan hardware.  Emulator output must not be recorded as a hardware
measurement.

## Performance boundary

Wait-state OFF performs two additional flag-preserving ARM instructions for
each instruction-stream byte.  There is no extra call and no extra memory load
in that path.  The DSpico cache is not consulted by the timing code.

DSpico testing confirmed that the OFF path does not introduce noticeable frame
pacing or audio regressions in the other tested games. The standalone ROM still
needs WonderSwan hardware measurements before its expected timing vectors can
be treated as authoritative.
