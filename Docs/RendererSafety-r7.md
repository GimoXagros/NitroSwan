# r7 renderer safety and completed-frame coherency candidate

Status date: 2026-09-05. This work began as a development candidate based on
fork `main` `0a895e86829e8044d7fccfa51ad4e67ee5194c2d`. The user subsequently
authorized packaging it as `v0.7.7-custom.r8`; the historical r7 tag remains
unchanged at `06178156341d70fd876174272d04f5cb5d440a2b`. Runtime limitations
remain as recorded below and in `ReleaseValidation-r8.md`.

## Repository and build identity

The work is isolated on `fix/r7-renderer-safety-obj-coherency`. PR #9 was
confirmed merged. Its branch was not deleted because it remains checked out in
a worktree containing retained local build assets. PR #59 and PR #60 remain
Open/Draft at `b308a6b` and `de83792`; neither branch, code, review state nor
release was changed.

All recursive gitlinks remain the fork-main pins except Sphinx. Its one-line ABI
correction is an ordinary commit on the new fork branch
`fix/r7-renderer-callback-alignment`:

| Submodule | SHA |
| --- | --- |
| ARMV30MZ | `b989c01a73ebda2d28c81d145e80e4c9ca786587` |
| Shared | `a3e101edb1d989d3b9eb175e45e49898c3de7cf6` |
| Shared/Unzip | `63769d6d58ee5600293c1e1300e49e9031858fca` |
| Sphinx | `326330132dc168ca6f348688c64d66b33afda1f2` |
| WSCart | `9756f1230c262b6f98e8a3329b5172ec4dcf0d3c` |
| WSCart/WSRTC | `2cf9caa1178860d2be9bfc85aa6b2624f459e298` |
| WSEEPROM | `c168f3ed5ebc967b6adc2c4b41b2b502bcefd80a` |

Local toolchain: Wonderful ARM GCC 16.2.0, BlocksDS/ndstool
v1.22.3-dirty, GNU Make 4.4.1 and Python 3.14.6. The clean pre-change builds
were 567296 bytes: DS SHA-256 `59696053cc6c29f7a99b5c7b88c06ac0b6e8aa33cec3e773cafae96766277166`
and DSi SHA-256 `011b2b3eaf01d28e1c52284f18a0801f2daae0699c49b97e5a7fcdf2c76a43a7`.

## A2: ARM/C ABI result

The reviewed rule is SP mod 8 = 0 immediately before every relevant C
`BL`/`BLX`. Counts below are 32-bit stack words from an 8-byte-aligned public C
entry. Opcode-local saves are either absent or even and do not change parity.

| Entry path | Push chain before C | SP mod 8 | Preservation / correction |
| --- | --- | ---: | --- |
| normal frame completion | run 9, scanline 1, endFrame 1, gfxEndFrame 7, bridge 2 | 0 | gfxEndFrame changed from 6 to 7; bridge retains r12/spxptr and lr |
| direct gfxRefresh | wrapper 1, gfxEndFrame 7, bridge 2 | 0 | direct wrapper normalizes the nested contract |
| state-restore rebuild | rebuild 8, bridge 2 | 0 | separate entry; r4-r10/lr and r12/spxptr preserved |
| new WS frame | run 9, scanline 1, bridge 2 | 0 | r12/spxptr and lr preserved |
| palette byte write | run 9, V30 1, hook 4 | 0 | r0-r2/lr preserved; r0/r1 write contract retained |
| unaligned palette word write | run 9, V30 1, word wrapper 2, hook 4 | 0 | wrapper changed from 1 to 2 and preserves r2/lr |
| byte video-register write | run 9, V30 1, hook 6 | 0 | r0-r3, r12/spxptr and lr preserved |
| word video-register write | run 9, V30 1, word wrapper 4, hook 6 | 0 | Sphinx wrapper changed from 3 to 4 |
| direct word-register entry | word wrapper 4, hook 6 | 0 | direct and nested paths share an even-depth contract |
| host VBlank assembly calls | vblIrqHandler 4 | 0 | r4-r6/lr preserved before calculateFPS/scanKeys |

`tools/validate_renderer_abi.py` inspects the built DS/DSi objects and checks
seven concrete symbol bodies plus all ten path models. Both profiles pass.
`RENDERER_ABI_SELF_TEST=1` adds an ARM runtime sentinel which checks the C entry
alignment, SP recovery and r4-r11 preservation. The diagnostic binary is built,
linked and packaged, but has not run on ARM hardware in this task. Therefore
this is linked-object proof plus a prepared execution test, not a claimed
on-device pass.

## A3: restore/reset lifecycle result

Reset, ROM replacement and save-state load now use one ordered lifecycle:

1. Quiesce VCOUNT capture/replay and renderer publication, invalidating all
   pending/active slot indices before clearing private snapshots. VBlank leaves
   the currently displayed hardware frame intact while quiesced.
2. Restore or reset CPU, RAM, Sphinx registers, palette RAM and cartridge state.
3. Rebuild decoded tiles through Sphinx's existing dirty-tile path, then rebuild
   scroll, window, OAM and mapped palettes from the restored state without
   advancing frame counters, RTC or other slow I/O.
4. Commit only the finished generation for the following host VBlank, then
   enable capture for the next WS frame.

The old pre-restore ready state cannot publish because quiesce clears pending,
ready, active and published ownership first. Source/model tests cover
load-before-VBlank, load-with-ready, reset-before-VBlank, ROM A to B,
color/mono, 4bpp/2bpp, LCD off/on, repeated load/reset and generation wrap with
zero skipped. A live save/advance/load test is still pending on melonDS/DSpico.

## A4: completed-frame publication result

The old layout published OBJ offset and generation in separate stores. The
executable model reproduces an interrupt between those stores, allowing a new
bank to be labelled with the previous generation. A second boundary existed
between OBJ-ready and palette-ready stores.

The candidate uses three completed-frame slots. Each slot owns one coherent
descriptor, a 1KB OAM snapshot and the 512-byte OBJ palette half. The descriptor
also identifies the decoded OBJ tile generation and BG bank. All copies finish
before a short interrupt-disabled metadata commit; that same commit publishes
the matching palette slot. Host VBlank consumes one slot and uses its OAM,
OBJ tile generation, OBJ palette and BG bank together. Reset invalidates
publication before clearing storage.

The 16KB OBJ policy remains conditional. A dirty WS generation seeds one 16KB
main-memory bank, and host VBlank publishes that generation once. A clean WS
frame owns fresh OAM/palette metadata but does not seed or publish another 16KB
tile bank. The always-owned 1KB OAM copy (and 512-byte OBJ palette copy on color
hardware) is required so a later 75Hz WS completion cannot overwrite state
still awaiting the 60Hz host VBlank.

Metrics now have distinct clocks:

- `objSeedBytesFrame`: current emulated WS frame, 0 or 16384;
- `objPublishBytesHostFrame`: current host VBlank, 0 or 16384;
- `objTotalBytes`: cumulative seed, publication, owned OAM and color OBJ-palette
  transfer bytes, updated atomically;
- `objTilesConvertedWSFrame`, `objPublicationCount`, and
  `skippedCleanGenerationCount`.

This proves and repairs the ownership safety defect. It does not prove that the
remaining visible One Piece/Digimon motion symptom has the same sole cause.

## Trace and residual character-motion status

`WSC_VIDEO_TRACE=1` builds a diagnostic-only fixed-size RAM ring. Main-loop
flushes append `renderer-trace-r7-safety.csv` under the existing `nitroswan`
data folder. No ROM name, path, checksum, product ID or other game identity is
recorded. Rows correlate host VBlank, WS completion, scanline, sprite/OAM frame,
OBJ build/ready/published generation and bank, BG banks, palette slots,
mode, dirty count, seed/publication/total bytes, VCOUNT activity and palette
events/drops. `tools/analyze_renderer_trace.py` reports mixed ownership and
dirty-generation publication failures.

No fresh trace was captured: the available Codex computer-control surface did
not expose a native melonDS window, and the retained specialized patched
melonDS cache lab is not a general NitroSwan renderer oracle. Consequently:

- r7 versus safety-candidate generation traces: **NOT RUN**;
- residual character-motion root cause beyond the proven safety defect:
  **UNVERIFIED**;
- speculative line-142/line-144 timing, generic BG raster, DMA3, 1KB
  EMUPALBUFF and game-specific logic: **UNCHANGED**.

## Validation matrix

| Check | Result |
| --- | --- |
| Python regressions | PASS, 76 tests |
| repository/localization | PASS; 128 translations, 20615 non-ASCII glyphs |
| host C RTC/cache execution | SKIP locally; PASS in CI |
| DS and DSi/DSpico build | PASS |
| linked-object ABI validator | PASS, 7 symbols / 10 paths in both profiles |
| banner/header/executable ranges | PASS for all four package binaries |
| git diff check | PASS |
| ARM ABI sentinel execution | NOT RUN; binary prepared |
| reset/save/load emulator smoke | NOT RUN |
| DSpico gameplay/performance/audio/input/save | NOT RUN |
| native WonderSwan reference | NOT RUN |

Fresh scene status is **NOT RUN** for One Piece original/patched, Battle Spirit
1.0/1.5/Frontier, two normal WSC 4bpp controls, color 2bpp, mono WS, Rockman &
Forte and Mahjong Touryuumon. The local files were found and left untouched;
none are included in artifacts or commits. Historical r7 user results remain
valid as history but are not relabelled as candidate passes.

Full builds retained the four known warnings in both profiles: unused
`checkTimeOut`, two volatile cartridge-probe temporaries set but not used, and
the old-style `crc32` definition. No new warning was observed.

Fork CI [run 33941255575](https://github.com/GimoXagros/NitroSwan/actions/runs/33941255575)
completed successfully at candidate `bb85d20`: repository/localization checks,
76 Python tests, actual host C RTC and DSpico-cache vectors, DS/DSi builds,
linked-object ABI validation (7 symbols and 10 paths in both profiles), NDS
validation and artifact archival all passed. CI reported the same four known
warnings in each build profile.

## Gate decision and remaining blockers

The source/model/build portion of the A2-A4 gate passes. The ARM sentinel,
reset/load-state smoke, fresh melonDS scenes and DSpico scenes remain pending,
so the complete safety gate is **not yet closed**. Only non-invasive trace
support was added after the safety corrections; no Phase-E sprite timing change
was made.

Next action: run the ABI self-test once, then the normal DSi candidate through
the reset/save/load and scene matrix. If the visible motion defect remains, run
the trace build on the exact same input and analyze the CSV before changing
line-142/144 timing or tile conversion. PR #59 and #60 must remain separate.
