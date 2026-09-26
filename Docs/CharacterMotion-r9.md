# Character-motion follow-up candidate (r9)

Status: Draft follow-up to GimoXagros/NitroSwan#11, based on its head
`dffa5d6ac20c99bb27502a0a3d565c1189705ecc`. This is not a release note, stable
version change, complete character-accuracy claim, or speedup claim. The change
retains the existing guest sprite-table latch event and pairs the previously
latched sprite descriptors with the tile bank prepared for the visible frame.

## Diagnosis and scope

The line-zero `newFrame` path prepares/decodes the guest tile data. The existing
later sprite-table latch updates `wsvSpriteRAM` for the next visible frame, and
the former line-144 `gfxEndFrame` conversion consumed that newly latched table
while recording the line-zero tile bank. The synthetic linked-ARM probe observed
this content mismatch: baseline OAM tile IDs were `[1, 2]` where the prior-table
visibility oracle expected `[0, 1]`; an unchanged-latch control passed. The
candidate prepares OAM at normal line-zero begin from the already-latched list,
then snapshots it at existing frame completion. The latch event and its
scanline are unchanged.

The hardware source is uncertain at the exact boundary. WSdev describes sprite
table DMA on line 144 for use on the following frame
([Display/Sprites](https://ws.nesdev.org/wiki/Display/Sprites),
[Frame timing](https://ws.nesdev.org/wiki/Frame_timing)); older Mednafen code
copies after rendering line 142
([source](https://sources.debian.org/src/mednafen/0.8.9-1/src/wswan/gfx.cpp/)).
This candidate does not resolve that discrepancy or claim a native hardware
capture. Its oracle is which already-observed table content is visible in the
current emulated frame, not an assertion about exact copy-cycle timing.

## Evidence and reproducibility

`tools/validate_character_motion_runtime.py` executes actual linked ARM
instructions for latch copy, decoded tile transfer, OAM conversion, completed
frame slots, publication, scheduler continuation and restored-state rebuild. It
uses synthetic guest RAM; unrelated scroll/window/icon/slow-I/O services are
stubbed. It does not emulate DS DMA/cache timing, display scanout pixels, or a
game's behavior.

| Check | Baseline | Candidate result |
|---|---:|---:|
| Main sprite visibility/mode/control vectors | Final 10-case suite: 8 fail, 2 pass | 10 cases pass on DS and DSi: four video modes, unchanged control, three mode transitions, and scheduler resume from lines 141 and 143 |
| Existing linked renderer runtime suite | 17 cases/profile | 17 pass per DS and DSi profile |
| Linked renderer ABI | — | 8 symbols / 10 reviewed call paths pass per profile |
| Build/package checks | — | DS and DSi builds, localization/hygiene, 80 Python core tests, host C RTC/cache regressions, and NDS header/banner checks pass in the VIDEO writer clone |
| Actual One Piece/Digimon scene, savestate/NVRAM roundtrip, DSpico/native WS | Not run | NOT RUN; manual scene selection/retest remains pending |

The baseline source at the synthetic probe observed guest table `0x02074ce0`,
latch buffer `0x02005a20`, prior descriptor `0x20200000`, and newly copied
descriptor `0x40400001`; baseline completed OAM at `0x020d5894` used tile 1
(`0x00500058`) instead of expected prior-latch tile 0 (`0x00300038`). The
final candidate writer's DS probe addresses were guest table `0x02074cf0`, latch
buffer `0x02005a34`, completed OAM `0x020d58a4`; its DSi addresses were table
`0x02074f20`, latch buffer `0x02005a34`, and completed OAM `0x020d5ad4`. Candidate
DS and DSi both observed tile 0 at `0x00300038`, followed by tile 1 on the next
complete frame. Addresses are build-specific evidence, not stable interfaces.

Writer-reported test artifact hashes (local candidate test builds; not release
assets):

| Artifact | SHA-256 |
|---|---|
| `NitroSwan-DS-r9-motion-test.nds` | `cd95ed190cd900f62eefee851a0404e6bb7796ed27f407847863ac45edb0f9a4` |
| `NitroSwan-DSi-r9-motion-test.nds` | `7484d3a48beecc44525b0a6a438c58feb7f028de06530c6d95be91ab947377d4` |

The CI workflow retains the repository validator's established
`NitroSwan-*-0.7.7-custom.r9` executable and artifact names. Those CI outputs
contain this PR's candidate and tests; the inherited filename is not a release,
stable/version claim, or replacement of an existing public r9 asset. The
separately built local artifacts above use `r9-motion-test` names.

The new vectors also test repeated publication, four `gfxRefresh` calls, reset
and restore paths, and two consecutive completed guest frames with another
frame beginning before host publication. The restore-only prepare handles a
restore that resumes after line zero, preserving the immediately rebuilt OAM
through the following scheduler run. These synthetic tests are not a serialized
game save/load roundtrip. At line 143 the prior visible-frame latch is not
recoverable from the restored state, so the oracle there is continuity with the
immediate rebuilt image, not native partial-frame reconstruction.

## Coverage boundaries and separate issues

- One Piece Japanese original and Korean patch, Digimon Battle Spirit 1.0/1.5/
  Frontier actual fight scenes: pending manual input and same-scene A/B. No first
  bad game pixel has been connected to this synthetic mismatch; do not call the
  user-visible defect fixed until the same scene is retested.
- The vector's 2bpp modes verify OAM content only, not pixel correctness. VIDEO
  found a separate existing 2bpp tile-address/decode issue, explicitly not fixed
  here.
- VIDEO also found an independent BG active-bank lifetime counterexample when
  multiple guest frames build before host VBlank; this P0 patch defers it. Keep
  it separate from the sprite-motion cause.
- Upstream FluBBaOfWard/NitroSwan#59 and FluBBaOfWard/Sphinx#4 remain separate
  BG-only work. No upstream branch, callback ABI, palette restore, or scanline
  palette change is included in this follow-up.
- Existing #11's completed OAM-source, completed OBJ palette, and repeated-host-
  refresh BG replay fixes remain intact.

Draft upstream response (not posted; requires separate approval): “FluBBaOfWard/
NitroSwan#59 and FluBBaOfWard/Sphinx#4 remain BG-only. This character-motion
follow-up does not change those branches or import OBJ snapshots. Before
integration, please provide linked-ARM evidence that the actual `$01` callback
entry satisfies its 8-byte C stack-alignment precondition, and that save-state
restore safely quiesces/rebuilds active or pending palette replay. Keep the
existing no-event VCOUNT behavior, repeated active-frame base/delta replay,
1 KiB palette contract, and DMA3/window ownership.”

## Build/repro commands

Run from a checkout with the pinned dependencies and the same BlocksDS toolchain:

```sh
python3 tools/run_core_regressions.py
make -j2 NAME=NitroSwan-DS-r9-motion-test
make -j2 NAME=NitroSwan-DSi-r9-motion-test DSPICO_3DS_BUILD=1 \
  SPECS="$BLOCKSDS/sys/crts/dsi_arm9.specs"
python3 tools/validate_renderer_runtime.py build/NitroSwan-DS-r9-motion-test.elf
python3 tools/validate_renderer_runtime.py build/NitroSwan-DSi-r9-motion-test.elf
python3 tools/validate_character_motion_runtime.py build/NitroSwan-DS-r9-motion-test.elf
python3 tools/validate_character_motion_runtime.py build/NitroSwan-DSi-r9-motion-test.elf
python3 tools/validate_nds.py --ds NitroSwan-DS-r9-motion-test.nds \
  --dsi NitroSwan-DSi-r9-motion-test.nds
```

These commands do not substitute for manual game-scene A/B, DSpico, or native
WonderSwan validation.
