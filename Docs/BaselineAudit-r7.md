# r7 baseline audit — 2026-09-03 snapshot

This is a fixed-date snapshot of GimoXagros/NitroSwan, not automatically current
status. Scope: integrity, reproducibility, branch hygiene, safety audit and
documentation. No release/tag/version bump, no new accuracy feature, no residual
OBJ experiment. **Readiness: NOT READY for unrelated feature work**, pending the
ABI and restore/ownership safety findings below. Passing build/model tests must
not override that judgment. The maintenance changes are reviewable separately.

## Baseline identity and integrity

- Fork main and dereferenced `v0.7.7-custom.r7`:
  `06178156341d70fd876174272d04f5cb5d440a2b`.
- Annotated tag object: `328cb224bba9ae4d52b39ed479e091803d65a42a`.
- Published 2026-09-02 11:28:14 UTC; release remains untouched.
- Renderer baseline `869e81f` (internal WSC-VideoCore-r8-test); build tree
  `e31a53b8cd1b8197cabec15df9278eaff7adbcfc`, identical to the merge tree.
- Workspace `fork` means GimoXagros, `origin` means FluBBaOfWard. Local `main`
  remains `a3fa336`, behind upstream by one, and is checked out elsewhere.
  It has no unique commit relative to fork main; it was not rewritten.
- Fetch with tags encountered an existing conflicting `v0.7.7` tag. No overwrite:
  both remotes were subsequently fetched/pruned with `--no-tags`; r7 was checked
  independently. That conflict is not object corruption.
- Top-level `git fsck --full`: exit 0, three dangling blobs, no corruption.
  Dangling objects were preserved (no GC/prune). Recursive submodule fsck: all 7
  pass. Recursive status: clean, initialized, exact gitlinks below.
- A fresh remote clone of the pinned baseline fetched every gitlink, including
  the ARMV30MZ PR commit from its configured upstream URL. Detached checkouts
  are intentional; no submodule pointer or branch was changed.

| Submodule | Exact gitlink | Configured source |
| --- | --- | --- |
| ARMV30MZ | `b989c01a73ebda2d28c81d145e80e4c9ca786587` | FluBBaOfWard |
| Shared | `a3e101edb1d989d3b9eb175e45e49898c3de7cf6` | GimoXagros |
| Shared/Unzip | `63769d6d58ee5600293c1e1300e49e9031858fca` | FluBBaOfWard |
| Sphinx | `97bf9fe4fdbeb0f761b22fe8e1fa68b5670a364e` | GimoXagros |
| WSCart | `9756f1230c262b6f98e8a3329b5172ec4dcf0d3c` | GimoXagros |
| WSCart/WSRTC | `2cf9caa1178860d2be9bfc85aa6b2624f459e298` | GimoXagros |
| WSEEPROM | `c168f3ed5ebc967b6adc2c4b41b2b502bcefd80a` | FluBBaOfWard |

## Branch/worktree inventory and cleanup

Fork remote heads before cleanup: `main`, `agent/wsc-video-core-fix`,
`agent/todo2-bg-palette`, `agent/opcode-fetch-waitstate-upstream` (as expected).
After cleanup, the merged video head is absent; the maintenance branch is added
when pushed. No active upstream head is synchronized, renamed or rewritten.

Counts below are unique commits relative to fork main at audit start. A = fully
merged; B = active PR; C = unique commits. Occupied worktrees remain protected
even if class A. No stash was present in the shared top-level repository.

| Local branch before cleanup | Tip | Class / unique | Action |
| --- | --- | --- | --- |
| agent/fix-dspico-capitalization | 760ee58 | C / 1 | Keep |
| agent/nitroswan-0.7.7-custom | a1f5d10 | C / 2 | Keep |
| agent/nitroswan-0.7.7-custom-r2 | 9c17607 | A / 0 | Keep; occupied, modified submodules/untracked assets |
| agent/nitroswan-0.7.7-custom-r3 | 48189a3 | A / 0 | Keep; occupied, untracked release files |
| agent/onepiece-todo-r4 | 3079857 | A / 0 | Keep; occupied, untracked release files |
| agent/opcode-fetch-waitstate-upstream | de83792 | B / 2 | Protect #60 |
| agent/todo2-bg-palette | 8820f67 | B / 6 | Protect #59 |
| agent/v30-prefetch-hardware-vectors | da82c50 | C / 1 | Keep; occupied research |
| agent/v30-prefetch-research | 564e171 | C / 1 | Keep; occupied research |
| agent/wsc-video-core-fix | e31a53b | A / 0 | Delete local and fork head |
| experimental/opcode-fetch-waitstate | e87f55c | A / 0 | Keep; occupied, untracked artifacts |
| fix/onepiece-patched-identity | 3840253 | A / 0 | Keep; occupied |
| main | a3fa336 | A / 0 | Keep; occupied upstream checkout |
| release/v0.7.7-custom | 85bbdc2 | A / 0 | Delete local only (remote already absent) |

Deletion guards: PR #8 is Merged; video head exactly e31a53b; both deleted local
heads are ancestors of fork main, have empty `fork/main..head`, are not checked
out, and cross-repository open-PR searches for each head returned empty. The
clean video worktree was switched to `chore/r7-baseline-audit` first. Remote tip
was rechecked immediately before deletion. Branch names only were removed;
files were not deleted and commits remain recoverable through r7/main history.

| Existing worktree basename | Tracked state | Untracked / ignored files | Preservation |
| --- | --- | --- | --- |
| NitroSwan-0.7.7 | clean | 0 / 245 | unchanged |
| NitroSwan-0.7.7-dspico-test | modified ARMV30MZ/Sphinx gitlinks | 5 / 185 | unchanged |
| NitroSwan-onepiece-patched | clean | 0 / 171 | unchanged |
| NitroSwan-onepiece-todo | clean | 6 / 312 | unchanged |
| NitroSwan-opcode-waitstate | clean | 9 / 192 | unchanged |
| NitroSwan-opcode-waitstate-upstream | clean | 0 / 124 | unchanged |
| NitroSwan-r3 | clean | 6 / 445 | unchanged |
| NitroSwan-r6-release | detached d19a87b, clean | 0 / 156 | unchanged |
| NitroSwan-todo2-pr | clean | 0 / 639 | unchanged |
| NitroSwan-v30-prefetch-research | clean | 7 / 0 | unchanged |
| NitroSwan-v30-prefetch-vectors | clean | 0 / 16 | unchanged |
| NitroSwan-wsc-video-core-fix | clean before audit | 0 / 492 | now maintenance branch; ignored files retained |

Fresh baseline/candidate build clones are separate directories, not destructive
clean operations in the above worktrees. No ROM/BIOS/save was opened or moved.

## Cross-repository PR snapshot

All six entries were **OPEN / Draft**, head owner GimoXagros. Dates are UTC.

| Upstream PR | Head branch / exact SHA | Base SHA | Last update |
| --- | --- | --- | --- |
| NitroSwan [#59](https://github.com/FluBBaOfWard/NitroSwan/pull/59) | agent/todo2-bg-palette / `8820f67158820f7770ffd0bf8d2d2f561450966a` | `564e171fb93c2c11f98f38607493675727676c2c` | 2026-09-02 11:28:47 |
| NitroSwan [#60](https://github.com/FluBBaOfWard/NitroSwan/pull/60) | agent/opcode-fetch-waitstate-upstream / `de837923184219f075496928eda0bd2ded15cfad` | `564e171fb93c2c11f98f38607493675727676c2c` | 2026-08-31 16:12:29 |
| Sphinx [#4](https://github.com/FluBBaOfWard/Sphinx/pull/4) | agent/todo2-palette-hook / `3266de3e5b5e6fd65a2af6f4f4d35960b5e4b3c8` | `8b625f118caa5a58f09c9fb2a32e1d1b70746f78` | 2026-08-31 11:08:48 |
| Sphinx [#5](https://github.com/FluBBaOfWard/Sphinx/pull/5) | agent/opcode-fetch-waitstate / `025f1db11184e03887c3713ab1e557ca4e551721` | `8b625f118caa5a58f09c9fb2a32e1d1b70746f78` | 2026-08-30 12:40:16 |
| ARMV30MZ [#6](https://github.com/FluBBaOfWard/ARMV30MZ/pull/6) | agent/opcode-fetch-waitstate / `b989c01a73ebda2d28c81d145e80e4c9ca786587` | `146f5fb4d664f8874792299d3a6e4bd8415df287` | 2026-08-30 12:39:31 |
| WSRTC [#2](https://github.com/FluBBaOfWard/WSRTC/pull/2) | agent/rtc-edge-fixes-v2 / `7ade8f88c1955f03b427090d1e27e8ba62b518b3` | `1ec3969c925397d9defabee81d5190a34f1271d5` | 2026-08-23 14:53:35 |

PR #59's minimal Sphinx 3266de3 is deliberately distinct from main's 97bf9fe.
PR #60's proper prefetch request remains unresolved; the custom per-byte model
is not presented as upstream-approved. WSRTC #2 is not the current RTC gitlink.

Submodule branch inventory (report only; no deletion):

| Repository | Default main | Other remote heads and handling |
| --- | --- | --- |
| NDS_Shared | b006209 | agent/dspico-extra-ram-cache a864c2b: historical alternative, retain; agent/nitroswan-shared-r3 a3e101e: pinned, protect |
| Sphinx | 8b625f1 | agent/onepiece-r4-opcode-waitstate 71968e8; agent/onepiece-r4-video 213e1d9; fix/write-time-video-hook 0eefeba: historical candidates for separate ancestry/PR review only; agent/opcode-fetch-waitstate 025f1db and agent/todo2-palette-hook 3266de3: active PRs; agent/wsc-video-core-fix 97bf9fe: pinned, protect |
| ARMV30MZ | 146f5fb | PrefixFix fac8888, fastPC 8354eaf, safePC 9061a61: distinct experiments, retain; agent/opcode-fetch-waitstate b989c01: active PR/pinned |
| WSCart | a817134 | agent/nitroswan-dspico-rom-cache-r3 9756f12: pinned; agent/update-wsrtc-calendar 099532d: historical candidate, separate review needed |
| WSRTC | 2cf9caa | agent/rtc-calendar-corrections 2cf9caa: duplicate tip candidate only; agent/rtc-edge-fixes-v2 7ade8f8: active PR |
| Unzip / WSEEPROM | pinned main | No additional heads observed |

## Source safety audit and disposition

No Critical memory overrun was reproduced within valid runtime input/state
bounds. This is not proof of memory safety for corrupt save files or arbitrary
interrupt schedules. Tests were added before the minimal palette fix: three
new source assertions failed on the unmodified baseline, then passed after it.

| ID / severity | Finding and evidence | Disposition |
| --- | --- | --- |
| A1 / High, fixed | Palette handoff could reuse active storage: finished=0, active=1; publish ready=0; load active=1; VBlank consumes ready into active=0 and clears ready=-1; load ready=-1; nextFree chooses 0. Baseline GCC output loads active at +0x172 and ready at +0x174, so this is not just unspecified C argument-order speculation. | Pin finishedFrame locally and always exclude it, whether the IRQ consumed ready or not. No IRQ masking, DMA change, copy-count or scanline timing-model change. Exhaustive small-state model covers handoff IRQ slots. |
| A2 / High, open ABI requirement | C -> run pushes 9 words; wsvDoScanline 1; endFrame 1; gfxEndFrame 6; C-call save 2. Normal frame-complete C call SP is 4 mod 8. Memory palette hook similarly has different aligned/unaligned-write caller depths. r0/r1 preservation alone is not an ABI proof. | Do not casually add one push register: direct gfxRefresh and other entry paths have different depths. A complete callback/stack-entry repair needs ARM execution tests, including Sphinx register-write/word/DMA entries. Not treated as hardware-confirmed crash; readiness blocker until repaired safely. |
| A3 / High, open restore lifecycle | unpackState restores WS RAM and Sphinx state, but not PaletteRaster/ObjTileBuffer ownership. sphinxLoadState clears dirty markers and redraws tiles using existing offsets; no coordinated custom generation/palette reset occurs. Existing readiness may still describe the pre-load scene. | A lone reset call after drawFrameGfx would erase rebuilt snapshots; a reset before it also requires palette-base and completion handling. Coordinated restore test/fix deferred rather than inserting an unverified renderer reset. Readiness blocker. |
| A4 / High safety follow-up, visible impact unproven | OBJ pointer and generation are separate stores. If ready=7/published=6, next completion stores the new offset, then VBlank can label that snapshot generation 7 before generation=8 is stored. gfxEndFrame rotates OAM buffers after the C publication calls. Reset clears snapshots before disabling publication. | Correct misleading 'safely defers' comment; preserve r7 ordering/copy behavior. Need unified reset/metadata/OAM ownership proof, not a standalone pointer patch falsely advertised as fixing character motion. Readiness blocker for safety sign-off; the known motion P0 remains a separate hardware investigation. |
| A5 / Low, fixed | lineStart[145] was written/reset but never read by any replay path, ABI, serializer or external module; replay uses delta/replayCursor. | Remove private array and its obsolete loop; 870 bytes of array storage removed across 3 frames (layout/alignment may affect final size). No event contents/order or replay algorithm change. |
| A6 / Medium, clarified | objBytesCopiedFrame counts 16KB seed only; omits host-VBlank 16KB publication. No external reader beyond declarations/docs found. | Explicit seed-only header/documentation; full metrics deferred because WS-frame reset and host-VBlank publication have different boundaries. |
| A7 / Medium/Low, fixed | Hardcoded personal compiler path, unchecked cross compiler, ambiguous skip; executable bit on 3 VS Code JSON files; stale documentation claims. | Portable compile/run probe, strict CI host requirement, hygiene validator/tests, mode-only JSON correction and docs. |

Why not fix A2-A4 by trial here: these require changing callback/lifecycle or
cross-buffer renderer publication, with multiple entry paths. The task prohibits
new residual-OBJ implementation and speculative renderer timing changes. The
audit therefore does NOT claim all High findings are solved or mark READY. This
is an explicit boundary, not a claim that the known graphical limitation alone
prevents baseline readiness. Resolve the safety prerequisites first with a
bounded, separately verified change before unrelated feature work.

### Bounds, ABI, ownership and transitions checked

- OBJ: offsets 0/512 xor 0x200, 512 * 32 = 16KB, two snapshots = 32KB;
  packed/planar conversion restricts OBJ writes below 0x4000. BG: offsets
  0/0x8000, 32KB banks at main BG VRAM +0x8000 and +0x10000, tile-base 2/4.
- DIRTYTILES allocates 0x800 bytes; color marker reads/invalidations span
  [0x200,0x600), mono [0x100,0x200). Group-of-four reads have divisible counts.
- Palette capture accepts FE00-FFFF; source index 0-255 stays in 512-byte WS
  palette RAM. BG events write indices 0-127 only; backdrop maps to BG index 0.
  384-entry cap holds; source lines 0-142 produce next lines 1-143, DS VCOUNT
  25-167 (screen top 24). Line 143 produces no visible next-line event; blanking
  updates base. EMUPALBUFF remains 0x400 and DMA3 remains window/OAM/palette DMA,
  never raster storage/transport. Existing tests are A/B, not actual scanout.
- Memory.s preserves r0/r1/lr around C on the palette path; r2/r3/r12 are
  caller-clobbered. Gfx.s saves spxptr/r12 and lr around its C calls; Sphinx
  register callback saves r0-r3/spxptr/lr. Stack alignment is the separate A2 gap.
- capture is the main emulation writer, ready is a completed candidate, active
  and replayCursor belong to VBlank/VCOUNT. A1 now prevents capture from choosing
  the published palette frame despite IRQ consumption. This is not a whole
  renderer memory-order proof or a reset/restore proof.
- VBlank order is unchanged: videoTileBufferVBlank publishes OBJ/sets BG base;
  vblIrqHandler handles OAM, full EMUPALBUFF transfer, scroll/window DMA and maps;
  paletteRasterVBlank restores BG-only base and arms sparse replay AFTER the
  full palette transfer. Moving it earlier could overwrite that base. OAM/tile
  generation pairing remains A4, not something a source-order test can certify.
- Packed/planar and 2bpp/4bpp mode changes invalidate format-specific markers
  after initialization. Mono disables snapshot publication; no host-model test
  certifies every mid-frame transition. Startup/ROM load/reset/eject call
  paletteRasterConfigure; save-state load does not. BIOS/reset/LCD transitions
  and pending IRQs need integration coverage; backdrop selects default color
  when LCD is off. No claims of complete transition validation.
- Metrics: seed bytes per WS frame are bounded 0/16384, maximum likewise, so
  those u32 values do not overflow. Cumulative swap/generation counters can wrap
  after 2^32 increments (about 659 days at 75.47 Hz); wrap/collision stress is
  pending. Palette dropped count is u16 and can wrap under extreme synthetic
  writes (telemetry issue, not a list overrun). No total-bandwidth claim.
- Diagnostic capture/replay/BG modes remain explicit opt-in build choices;
  shipped default is BG-only. No diagnostic autoload or extra renderer flag
  added. drawFrameGfxAtVBlank is a retained no-op line-state target, not removable
  by grep alone. Existing banner verifier is a manual helper; CI uses the newer
  header/banner validator. Legitimate generated font/Metis IPL assets retained.

## Validation and build evidence

Fresh 0617815 clone, exact recursive gitlinks, local Windows/MSYS2 toolchain:

- BLOCKSDS: `/opt/wonderful/thirdparty/blocksds/core`, version `v1.22.3-dirty`.
- Wonderful: `/opt/wonderful`; GCC at `toolchain/gcc-arm-none-eabi/bin`, 16.2.0.
- ndstool: `v1.22.3-dirty`; GNU make and Python 3.14 used locally.
- Host C compiler absent locally: explicitly SKIP; CI installs host GCC and
  must execute RTC and ROM-cache C vectors (REQUIRE_HOST_CC=1).
- Localization PASS: 128 translations, 20615 non-ASCII glyphs, Korean/Japanese.
- Maintenance compileall and Python source/model/tooling regressions PASS:
  65 tests at this stage. Some tests reproduce old/open counterexamples; see
  their names and source rather than interpreting all as positive safety tests.
- Baseline DS/DSi builds and header/banner checks PASS. Both headers use unit
  code 2; profiles are distinguished by specs/build flags, not unit byte alone.

| Build | Bytes | Fresh baseline SHA-256 |
| --- | ---: | --- |
| DS | 567296 | `3d7e2ddbc2123127eb789170cead2bc5c58fbc8dcf58cd3d41b82a3bd30a3c02` |
| DSi/DSpico | 568320 | `08cb4dbb5fe8e9db3030a400d09743a471878612e356fbd63d47dcf595998bbc` |

Published checksums differ. Byte inspection and LZ10 decoding found 42 DS / 46
DSi differing bytes: 40 at header authentication offsets 0x300-0x313 and
0xFEC-0xFFF, plus 2/6 unused tail-padding bytes in generated graphics arrays.
Decoded graphics are identical, and no other byte differs. Specifically:

| Profile / compressed symbol | Consumed / allocated compressed bytes | Identical decoded bytes |
| --- | ---: | ---: |
| DS SCBottomTiles | 1246 / 1248 | 4128 |
| DSi SCBottomMap | 323 / 324 | 384 |
| DSi SCBottomTiles | 1246 / 1248 | 4128 |
| DSi EmuFontTiles | 2113 / 2116 | 4096 |

Thus this baseline/release comparison found non-semantic generated padding,
not changed instructions or corrupt decoded assets. Bit-for-bit repeatability
still needs tool-side padding normalization in a separately scoped task; no
binary is patched or re-uploaded by this audit. Do not generalize this result to
arbitrary differing hashes or to the changed maintenance candidate.

Warnings in BOTH baseline profiles (all pre-existing; no warning suppression):

| Warning | Classification / disposition |
| --- | --- |
| Main.c:208 checkTimeOut unused | Existing disabled sleep/debug path; leave |
| Shared/CartridgeRAM.c:44 tmp set but unused | External submodule hardware-probe read; do not delete volatile access |
| Shared/CartridgeRAM.c:88 tmp set but unused | Same category; leave |
| Shared/crc32.c:23 old-style definition | External upstream style warning; document |

No fresh emulator/DSpico gameplay or native WonderSwan run is claimed. Historical
r7 hardware scope remains in ReleaseValidation-r7.md. No private asset is needed
or published. Hygiene scans tracked text recursively and deliberately ignores
untracked local assets; unknown binary content still requires human review.

## Final candidate / PR evidence

Clean remote clone plus exact candidate checkout:
`a95c96fc575ca1d26851192bc834e918079e355b`. Recursive gitlinks unchanged.
Compileall, repository hygiene (181 recursive tracked entries), localization,
65 Python tests, DS/DSi build and NDS validation all PASS. Local host C explicitly
SKIP (no working host compiler). No new compiler warning; the same four warnings
listed above occur in each profile. Both banner icon/palette, CRCs, six language
title slots and executable ranges pass the existing validator.

| Candidate artifact (not a release) | Bytes | SHA-256 |
| --- | ---: | --- |
| NitroSwan-DS-0.7.7-custom.r7.nds | 567296 | `1ea06f2645d62f8e6a6eaa0039ca0f059c843ebefe66bcb752c94a184337ddc4` |
| NitroSwan-DSi-0.7.7-custom.r7.nds | 567296 | `b54a9aeb377ae6910261b8232e3bc1dc508202b929242d3c803ffea2aaba2a81` |

These differ intentionally from r7 because the dead line-index code/storage was
removed and the palette ownership defect fixed. No application version, feature
flag, OBJ copy count, emulated scanline event, DMA assignment or VBlank call order
changed. Host instruction count/code layout necessarily changes; no performance
or hardware certification is inferred from this maintenance build.

Initial commits: tooling `99f4b52`, documentation `ef0890c`, minimal palette fix /
dead-state cleanup / audit counterexamples `a95c96f`. A following documentation
commit records these results; source/build inputs are unchanged by that record.
Draft PR and CI status are recorded once the remote run completes. Main,
release/tag, History dates and all active PR/gitlink pointers remain unchanged.

## Next work recommendation

Do not create a feature branch in this task. First close A2-A4 with ARM callback
and restore/interleaving tests on a proposed `fix/r7-renderer-safety-contracts`
branch. After safety sign-off, `fix/r7-obj-generation-coherency` is the suggested
P0 investigation branch, not an assertion of the remaining motion bug's cause.
First target: prove aligned C entries and coherent state restoration under an
injected pending VBlank, then correlate OAM/tile/latch/palette generations in the
same One Piece and Battle Spirit Frontier scenes while BG controls stay intact.
