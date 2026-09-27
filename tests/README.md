# BG palette regression checks

These checks target the BG-only upstream PR, not the custom OBJ/BG-bank renderer.
Sphinx remains pinned at `3266de3`; no tile destinations or guest timing changed.

Build with the existing BlocksDS Makefile, retaining older artifacts:

```sh
make NAME=NitroSwan-pr59-alignfix-DS-20260927 COMPDB=0
make NAME=NitroSwan-pr59-alignfix-DSi-20260927 COMPDB=0 \
  SPECS="$BLOCKSDS/sys/crts/dsi_arm9.specs"
```

The second command selects the toolchain's standard DSi linker specification,
not a custom DSpico ROM-cache profile. The repository CI's default remains DS.
Diagnostic builds can use separate names and `PALETTE_RASTER_DIAGNOSTIC=1`
(capture only) or `=2` (replay only). Runtime expectations below target the
default BG replay build, not those diagnostic configurations.

Python 3 with `unicorn` and `pyelftools` is required for instruction tests
(tested with Unicorn 2.1.4):

```sh
python -m unittest discover -s tests -v
python tests/validate_palette_runtime.py build/NitroSwan-pr59-alignfix-DS-20260927.elf
python tests/validate_palette_abi.py build/NitroSwan-pr59-alignfix-DS-20260927.elf
```

Repeat the two ELF commands for the DSi artifact. Any failing case returns a
nonzero status. The scripts also accept older linked upstream ELF files and
retain strict expected values for before/after counterexamples.

Coverage:

- Seven source/model checks retain the completed-slot IRQ-handoff regression
  and check lifecycle call sites and BG-only scope.
- Twenty-two linked ARM cases compare mono/color-2bpp output against actual
  `paletteTxAll`, exercise completed-versus-live mode, retire stale replay,
  invalidate observed mixed captures, repeat event-free/eventful frames, and
  remap completed raw RGB12 colors after a host palette change.
- The real `unpackState` wrapper and RAM copies execute while serialization
  engines are stubbed. This checks quiesce/reseed and palette rebuilding, not
  save-file format or whole-game restore accuracy.
- Thirteen linked ABI cases observe SP at actual C entries: register callback
  incoming SP mod 8 of 0/4, Sphinx byte/word register dispatch, byte/unaligned
  word palette writes with incoming SP mod 8 of 0/4, real byte/word DMA-start
  register writes to port 0x48, normal nested frame completion, direct refresh,
  and actual `stepScanLine` execution of a synthetic guest palette-write program.
  The frame cases stub tile/OAM work and supply its reviewed caller stack
  contract. The stepping case executes the CPU and stubs only post-CPU scanline
  rendering. These are bounded paths, not an exhaustive guest-program test.

The host register-callback assembly shim preserves its incoming SP, r4 and LR
and aligns the nested C call. Sphinx's six-register hook preserves incoming
alignment; it does not itself establish alignment. The host shim also handles
the existing Sphinx word-write path without modifying that dependency.
The palette-RAM callback similarly normalizes incoming SP, preserving r0/r1,
r4 and the original SP. A fixed-size push alone was insufficient for word-I/O
DMA and debug stepping; both have executable counterexamples in this suite.

Eligibility records modes observed at capture boundaries and palette/backdrop
callbacks; a transient mode excursion with no such observation is not tracked.
The fallback preserves the legacy palette, not native mixed-mode scanout.
These are synthetic RAM/MMIO instruction checks, not DS DMA timing, hardware
boot, game screenshots, or exhaustive callback/IRQ-interleaving certification.
Custom-release hardware results must not be attributed to this upstream binary.
