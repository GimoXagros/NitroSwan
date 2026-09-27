# r10 rendering and ROM-switch release validation

Date: 2026-09-27. Release: `v0.7.7-custom.r10` integrates stabilization
[fork PR #11](https://github.com/GimoXagros/NitroSwan/pull/11) and follow-up
[PR #12](https://github.com/GimoXagros/NitroSwan/pull/12) into main.
The user explicitly authorized release and merging/organizing both PRs after reporting the character,
Rockman & Forte and background palette problems resolved on physical hardware.
Prior r8/r9 tags and assets are retained without rewriting history.

## Corrections since r9

- Prepare visible-frame OAM from the sprite descriptors already latched for
  that frame, before the later latch overwrites them with next-frame data.
  Preserve restore/refresh behavior and the existing guest latch event.
- Stop renderer-owned repeat HBlank DMA 0/3 using the SDK safe-stop helper
  before reset/ROM replacement reuses buffers. Merely gating future VBlanks
  did not stop transfers already armed. No disk I/O is added inside this span.
- Fix the Sphinx 2bpp destination register: apply the BG bank offset to r7/r8,
  not fixed OBJ base r9. This is a custom BG-bank integration correction.
- Store direct-color replay eligibility with each completed palette frame.
  Mono and color 2bpp retain `paletteTxAll` expansion even on color-capable SoCs;
  unsupported completed frames retire older replay. IRQs inspect the selected
  completed flag, not the mode of an unfinished next guest frame. Eligible
  color 4bpp still replays its base/events on repeated host refreshes.

No game whitelist, new CPU timing model, OBJ palette raster, EMUPALBUFF growth,
DMA3 palette reuse, save-format change or speculative speed optimization.

## Hardware evidence and artifact boundary

The user reported One Piece/Digimon battle trails resolved on the motion test,
then Digimon -> One Piece -> Dicing Knight ROM switches working after the DMA
quiescence fix. Rockman still lost its backgrounds with Machine forced to
SwanCrystal, while Auto worked. After the crystal-mono palette test, the user
confirmed Rockman & Forte, background palette and character problems resolved
and requested this release. These are user-operated DSpico/3DS observations,
not independently captured native WonderSwan vectors or a whole-ROM matrix.

Latest hardware test offered: `NitroSwan-DSi-r9-crystal-mono-test.nds`, SHA-256
`ab9ba8790ab679c7697703cf0fb28c8a076fad126bac0e82da8d9df48c41da6e`.
The final r10 binaries rebuild that runtime source with the About version/date
changed and the Sphinx fix pinned to a published commit. Final-name binaries
have automated checks, not a separate post-renaming physical test. Do not infer
DS/DS Lite hardware certification or identical hashes from the DSi result.

## Automated validation

| Check | Scope |
|---|---|
| Repository/localization | Current filenames, source version, hygiene and glyph coverage |
| Core | 80 Python cases plus actual host C RTC/cache executables |
| Each DS/DSi linked ELF | Renderer 17, character motion 10, DMA quiescence 4, 2bpp destination 10, palette mode 19: 60 cases/profile |
| Each linked ABI | 8 symbols / 10 call paths |
| NDS | Header CRC, executable ranges, embedded logo/banner and six titles |
| Independent candidate review | No actionable scoped defect; independent ARM reruns passed |

The palette control test on the prior Rockman candidate fails 10/19 cases;
the corrected test candidate passes 19/19. Its oracle calls the actual linked
legacy palette conversion. Tests include repeated refresh, mono/color2bpp,
planar/packed 4bpp, completed-vs-live mode, sticky invalidation, restore, stale
IRQ retirement and recovery back to color. Synthetic MMIO does not reproduce
DMA/cache timing or scanout. Core source/model tests are not game execution.

Toolchain: Wonderful GCC 16.2.0, BlocksDS/ndstool v1.22.3-dirty. Four existing
warnings per profile remain: unused checkTimeOut, two unused CartridgeRAM tmp
variables, old-style crc32 definition. No toolchain or unrelated dependency
upgrade. Release `BUILD_INFO.txt` and `SHA256SUMS.txt` record the exact final
source/gitlinks, options, artifact hashes and validation outcome.

## Dependency

Sphinx: `9bf5031aaad3070a39ece6763a31820664b45414`, published on
GimoXagros/Sphinx `fix/2bpp-bg-tile-offset`, parent
`326330132dc168ca6f348688c64d66b33afda1f2`. Only the destination instruction and
its explanatory comments change. Other submodule pins remain as in r9.

## Remaining limits

- An independently identified BG bank-lifetime counterexample with multiple
  guest frames before host publication remains separate, with game impact not
  established by these scene reports. Preserve it for targeted follow-up.
- The replay flag observes palette/backdrop callbacks and frame boundaries.
  A transient unsupported mode and return without an observed callback/end is
  not tracked. Full mixed-mode scanline palette rendering is not implemented.
- Full ROM/BIOS/LCD/reset/failing-load/save roundtrip matrices, fresh controlled
  melonDS A/B game captures, audio/performance measurements and native WS timing
  were not completed for r10. Prior results are not relabelled as new tests.
- No complete One Piece J/K or all Battle Spirit variant certification; retain
  the user's verified scenes as controls and expand coverage separately.

## Reproduce final builds

```sh
python3 tools/validate_repository.py
python3 tools/validate_localization.py
REQUIRE_HOST_CC=1 python3 tools/run_core_regressions.py
make -j2 NAME=NitroSwan-DS-0.7.7-custom.r10
make -j2 NAME=NitroSwan-DSi-0.7.7-custom.r10 DSPICO_3DS_BUILD=1 \
  SPECS="$BLOCKSDS/sys/crts/dsi_arm9.specs"
```

Run `validate_renderer_runtime.py`, `validate_character_motion_runtime.py`,
`validate_quiesce_dma_runtime.py`, `validate_2bpp_runtime.py` and
`validate_palette_mode_runtime.py` against both `build/<NAME>.elf` files.
CI additionally runs `validate_renderer_abi.py` and `validate_nds.py` on both
profiles. Use the pinned submodules, never `submodule update --remote`.

Keep prior releases and back up settings/saves before manual comparisons.
Check Rockman title/UI/map under SwanCrystal and Auto, One Piece sky and large
motions, Digimon combat, and the reported three-game switch sequence. Keep game
ROM/BIOS/save/video data local; no private test assets are in the release.
