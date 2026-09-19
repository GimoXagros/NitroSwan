# r9 stabilization prerelease validation

Date: 2026-09-19. Baseline: fork main / r8 at
`20ce30634dab50fc95c369833b5f033da38fe2cd`.
This is a separate Draft PR candidate, not a main merge. The user's explicit
r9 prerelease request supersedes the attached plan's default no-release rule.
Previous releases, protected upstream PRs and all dependency pins are retained.

## What is corrected

1. The VBlank scroll `ldmia` overwrote the completed OAM pointer in r4 before
   OAM DMA setup. Preserve that pointer in r5 until its last use instead.
2. Publishing a completed OBJ palette wrote into the interrupted WS frame's
   live EMUPALBUFF. Publish to host OBJ palette RAM after the legacy DMA instead.
3. A repeated host refresh with no ready WS frame stopped BG palette replay.
   Reapply the active base and events; event-free frames still disable VCOUNT.
4. Renderer quiescence also stopped `scanKeys`, leaving initial menus without
   their periodic input scan. Sample input independently in `myVblank`.

The first three defects have executable linked-ARM counterexamples. The input
case observes zero scans before and one after the fix. They are not proof that
the user's remaining motion artifact has been completely resolved.

The review also identified stale paused Gamma/Contrast colors and a root-only
trace path. Host palette changes now rebuild completed display state without
resetting tiles or advancing guest time. Old mapped raster deltas are discarded;
fresh gradients are captured when guest execution resumes. Trace capture retains
the actual data-directory path selected by the existing folder lookup.

## Evidence levels

| Check | Result / limit |
|---|---|
| r8 baseline Python | 76 tests PASS |
| Candidate Python | 80 tests PASS (source/model/tooling, not game compatibility) |
| Host C | RTC calendar and DSpico cache vectors PASS |
| Linked ARM runtime | 15 synthetic cases per candidate DS/DSi ELF PASS; r8 fails 9 of 14 applicable cases |
| Optional ABI sentinel | Compiled ARM sentinel PASS in Unicorn; device execution NOT RUN |
| Object ABI | 7 symbols / 10 reviewed stack paths, both profiles |
| Packaging | Both NDS header CRC, executable ranges, six banner titles/icon CRC |
| melonDS 1.1 | Fresh DS candidate boot and touch-opened file browser observed |
| Paired game scenes | BLOCKED: automated scene selection/capture not established |
| Full game/save/audio matrix | NOT RUN for r9; no historical results relabelled |
| DSpico and native WS | NOT RUN |

The ARM runner uses actual linked instructions with synthetic memory/MMIO. It
stubs unrelated FPS/input service routines, does not emulate DMA/cache timing or
render pixels, and therefore cannot certify real-hardware correctness. It checks
callee-saved registers and balanced stacks on every invoked entry. Lifecycle
cases cover buffer reset, restore, repeated publication, 2bpp/4bpp, packed/planar
selection and generation wrap, not complete game savestate round trips.

Native smoke-test limitation: melonDS's homebrew auto-injection changed the
existing test SD image despite the requested read-only setting. Native testing
was stopped. A read-only image audit found the two injected test executables,
164 files identical to their host copies and one pre-existing save whose difference
from the host copy cannot be dated without a before-file inventory. No rollback
or save overwrite was attempted. A private incident report is retained locally.
Future native tests must use explicitly disposable media, not trust the frontend
read-only switch. This incident is not a game-save compatibility PASS.

## Reproduce

Install Python 3, a native C compiler, `unicorn`, `pyelftools`, and the project's
BlocksDS/Wonderful ARM toolchain. Run:

```sh
python3 -m compileall -q tools tests
python3 tools/validate_repository.py
python3 tools/validate_localization.py
python3 tools/run_core_regressions.py
make -j2 NAME=NitroSwan-DS-0.7.7-custom.r9
make -j2 NAME=NitroSwan-DSi-0.7.7-custom.r9 DSPICO_3DS_BUILD=1 \
  SPECS="$BLOCKSDS/sys/crts/dsi_arm9.specs"
python3 tools/validate_renderer_runtime.py build/NitroSwan-DS-0.7.7-custom.r9.elf
python3 tools/validate_renderer_runtime.py build/NitroSwan-DSi-0.7.7-custom.r9.elf
python3 tools/validate_nds.py --ds NitroSwan-DS-0.7.7-custom.r9.nds \
  --dsi NitroSwan-DSi-0.7.7-custom.r9.nds
```

CI also checks both linked ABI objects. Local toolchain: Wonderful GCC 16.2.0,
BlocksDS core version file `v1.22.3-dirty`, ndstool `v1.22.3-dirty`.
The four pre-existing compiler warnings are unused `checkTimeOut`, two unused
Shared/CartridgeRAM temporaries, and Shared/crc32's old-style definition.
They are not silently rewritten in dependency submodules.

## Diagnostic interpretation

`WSC_VIDEO_TRACE=1 RENDERER_ABI_SELF_TEST=1` enables the optional diagnostic build.
It appends `renderer-trace-r9.csv` to the selected NitroSwan data folder, including
the supported `/data/nitroswan` layout. Do not compare its speed with release
binaries: disk logging and longer critical sections perturb execution.

- W rows observe completed metadata before an IRQ can consume the ready slot.
- V rows observe actual OAM DMA source ownership, host publication and replay.
- `epoch` separates reset/restore generations. `ticks` uses ARM9 timers 2/3 at
  BUS_CLOCK/64; unsigned subtraction handles a single wrap. `timer_available=0`
  means another owner prevented timer reservation; zero is not measured time.
- `vblank_ticks` includes input/publication/replay setup, excluding CSV I/O;
  it is not guest CPU cycles or a hardware performance result by itself.
- OBJ seed/dirty and BG seed values belong to W rows; OBJ publication bytes to
  V rows. `obj_total_bytes` counts seed, OAM/palette snapshot, and OBJ tile
  publication only, not every bus transfer. Do not sum a cumulative counter.
- `sprite_latch_frame=4294967295` explicitly means unobserved. The analyzer
  returns BLOCKED for missing observations, record loss, malformed/empty traces,
  or missing clock domains instead of claiming end-to-end ownership PASS.
- OAM conversion/latch counters, ROM-cache hit/miss, audio underrun, save/load
  duration, dirty-tile identities and paired real-scene pacing remain unmeasured.
  The existing dirty count is a count of conversion candidates, not an independent
  completed-conversion counter. These are follow-up measurement gates.

## Manual DSpico A/B procedure

Keep r8 and all existing saves. Back up saves to a separate location before any
write tests. Use the DSi r9 binary with DSpico/Pico Loader, the DS binary only for
DS-mode loaders. Check the supplied SHA256SUMS.txt before copying.

1. Cold boot to the menu, navigate before loading any ROM, then direct-launch a
   ROM from Pico Loader. Both must accept input and finish loading.
2. Repeat the same One Piece J/K and Battle Spirit 1.0/1.5/Frontier scenes as r8:
   character selection, battle start, large attacks/jumps and rapid direction
   changes. Record any split/stale character tiles, residual trails and BG issues.
3. Pause in Display, change Gamma and Contrast, then resume. Check game colors,
   sky/gradients and sprites. Compare with event-free scenes and menu-only waits.
4. Reset, switch ROMs and alternate Mono/Color, BIOS on/off, LCD off/on where
   supported. Test save/load repeatedly using disposable copied saves only.
5. Check Rockman & Forte and the listed BG/timing controls in the TODO/matrix.
   Log graphics, audio, input, saves and speed separately; do not infer one from
   another. Suggested report: build hash, device/loader, logical scene ID,
   reproducible inputs, PASS/FAIL per category and a short video if it fails.

No new speed optimization is claimed. Conditional dirty-generation copies remain
unchanged; correctness fixes can add work on repeated frames. Measure release
builds on hardware before accepting any future copy/IRQ optimization.
