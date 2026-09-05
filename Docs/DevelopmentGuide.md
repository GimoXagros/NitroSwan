# NitroSwan development guide (r7 baseline)

This guide describes development procedure, not a hardware certification.
Read the dated [audit snapshot](BaselineAudit-r7.md) before starting: outstanding
safety findings must be closed before unrelated accuracy features. The current
release is `v0.7.7-custom.r8`; its remaining runtime gates are recorded in
[ReleaseValidation-r8.md](ReleaseValidation-r8.md).

## Repositories, branches and dependencies

The custom repository is [GimoXagros/NitroSwan](https://github.com/GimoXagros/NitroSwan);
the original is [FluBBaOfWard/NitroSwan](https://github.com/FluBBaOfWard/NitroSwan).
Check `git remote -v`: names are not identities. A new fork clone normally uses
`origin` for GimoXagros; the older audit workspace uses `fork` for GimoXagros and
`origin` for FluBBaOfWard. Do not rename someone else's remotes automatically.

```sh
git clone --recurse-submodules https://github.com/GimoXagros/NitroSwan.git
cd NitroSwan
git submodule sync --recursive
git submodule update --init --recursive
git status --short
git submodule status --recursive
```

Gitlinks are the dependency lock, including Shared/Unzip and WSCart/WSRTC.
Detached submodules are normal. Never use `submodule update --remote` as a
reproducibility check. Before changing a gitlink, review the dependency diff,
prove the exact SHA can be fetched remotely, build both profiles and document
the dependent PR. Do not replace main's Sphinx history with the minimal #59 hook.

Use `chore/` for maintenance, `fix/` for bounded fixes, `experimental/` for
unshipped experiments. Feature branches may follow custom main. Upstream-minimal
branches deliberately omit custom changes: being behind main is not a defect.
Protect cross-repository PR heads even if the fork itself has no open PR:

- NitroSwan `agent/todo2-bg-palette`: upstream #59; Sphinx #4 dependency.
- NitroSwan `agent/opcode-fetch-waitstate-upstream`: #60; Sphinx #5 / ARMV30MZ #6.
- WSRTC `agent/rtc-edge-fixes-v2`: #2, separate from the current RTC gitlink.

Before branch deletion, check all worktrees, unique commits, ancestor relation,
stash, dirty/untracked work and open PRs across repositories. Delete only merged,
unused branches with recoverable commit IDs; never delete submodule branches
as a side effect. Do not rewrite active PR history to synchronize it with main.

## Build prerequisites and commands

Use Git, Python 3.10+, GNU make, BlocksDS core libraries/tools, Wonderful
`arm-none-eabi-gcc` and both ARM9 specs. The local audit used GCC 16.2.0 and
BlocksDS/ndstool `v1.22.3-dirty`; this records the installed tools, not a claim
of an immutable or pristine toolchain. CI's `slim-latest` is likewise not pinned.
Use MSYS2 bash on Windows or a compatible POSIX shell; run each check separately
or stop the shell on failure. No ROM or private BIOS is required for baseline tests.

Typical environment (adjust to your actual installation, no personal path in Git):

```sh
export BLOCKSDS=/opt/blocksds/core
export BLOCKSDSEXT=/opt/blocksds/external
export WONDERFUL_TOOLCHAIN=/opt/wonderful
export PATH="$WONDERFUL_TOOLCHAIN/bin:$PATH"
python3 -m compileall -q tools tests
python3 tools/validate_repository.py
python3 tools/validate_localization.py
python3 tools/run_core_regressions.py
make -j2 NAME=NitroSwan-DS-0.7.7-custom.r8
make -j2 NAME=NitroSwan-DSi-0.7.7-custom.r8 DSPICO_3DS_BUILD=1 \
  SPECS="$BLOCKSDS/sys/crts/dsi_arm9.specs"
python3 tools/validate_nds.py --ds NitroSwan-DS-0.7.7-custom.r8.nds \
  --dsi NitroSwan-DSi-0.7.7-custom.r8.nds
```

`HOST_CC` selects a host executable path/name, not shell flags or a command
pipeline. The runner tries it, then PATH cc/gcc/clang, then explicit `CC`.
Every candidate must compile AND execute a probe. Missing host tools produce
`SKIP host C regressions`, not a false host PASS. CI installs GCC and sets
`REQUIRE_HOST_CC=1`, so it cannot silently skip host tests.

The DS profile defaults to `ds_arm9.specs`; DSi uses the explicit specs and
DSpico build flag above. BlocksDS may emit unit code 2 for BOTH: the header byte
alone does not prove a DSi-exclusive executable. `WSLogo.bmp` supplies the static
32x32 icon/banner via `GAME_ICON`; do not confuse `logo.png` with this build input.
Run Python validators without `-O` (the existing NDS validator uses assertions).

## Clean reproducibility and comparisons

Use a new directory, not cleanup commands on a working tree with private files:

```sh
git clone --no-checkout https://github.com/GimoXagros/NitroSwan.git NitroSwan-clean
cd NitroSwan-clean
git checkout --detach v0.7.7-custom.r8
git submodule sync --recursive
git submodule update --init --recursive
```

For a maintenance candidate, fetch and checkout its exact recorded commit instead
of the release tag, then repeat all tests/build commands. Record the full gitlink
list, compiler/tool versions, warnings, output sizes and SHA-256. Compare with the
release's BUILD_INFO and checksums. Different hashes need byte/section inspection:
generated compressed-asset padding and authentication hashes can differ without
different executable instructions. Never label a binary corrupt from SHA alone.
Preserve previous binaries and local reports; do not upload private test inputs.

## Private assets and evidence levels

Put commercial ROMs, external BIOS dumps and user saves in `.local-test-assets/`;
put local logs/recordings in `local-reports/`. Both root folders are ignored.
Do not include them in Git, PR attachments, Actions artifacts or releases.
A manifest may record a logical test ID plus SHA-256, never a local filename/path
or asset bytes. Renderer behavior must not be enabled by a ROM hash. Diagnostic
selection is distinct: [identity policy](GameCompatibilityIdentity.md).
There is no blanket `*.bin` ignore: tracked fonts and the upstream Metis IPL
replacement binaries are legitimate, reviewed build inputs.

| Level | Evidence | What it does not establish |
| --- | --- | --- |
| A | Source-contract checks | Execution correctness or IRQ safety |
| B | Python state/interleaving models | Actual ARM instructions or scanout |
| C | Host C executable vectors | DS peripherals/ARM ABI |
| D | DS/DSi assemble, link, package, header/banner checks | Gameplay correctness |
| E | Emulator/reference scene run | DSpico or native WS timing |
| F | DSpico on Nintendo 3DS/DSi | Native WonderSwan bus timing |
| G | Native WonderSwan hardware vectors | Untested games and states |

Most `test_graphics_core.py` tests are A/B. Some audit tests intentionally
reproduce an old/open counterexample; a passing assertion is not a safety pass.
Distinguish test source, exact binary/hash, machine, scene, manual operator,
observed result and untested limits. Historical release records stay historical.

## Before starting a task

1. Fetch without overwriting conflicting tags; compare main/tag/gitlinks to the
   dated audit instead of assuming its snapshot is current.
2. Inventory remotes, worktrees, stashes and private/untracked assets. Preserve
   unrelated work; use a clean worktree if needed.
3. Confirm cross-repository PR heads and the requested feature boundary.
4. Run integrity/hygiene/localization/regressions and both clean builds first.
5. Write a reproduction and evidence plan; choose a bounded branch from main.
6. Review the safety blockers before adding timing or rendering features.

For the residual OBJ P0, inspect Main.c, Gfx.s, Memory.s, PaletteRaster.c/.h,
ObjTileBuffer.c/.h, cpu.s, WonderSwan.c, Sphinx/WSVideo.s and the graphics/audit
tests. Capture the same One Piece original/patched and Battle Spirit 1.0/1.5/
Frontier scenes, alongside working BG and WS/2bpp controls. Record paired
OAM/tile/latch/palette/VBlank generations; preserve the line-142 latch,
line-144 conversion, 1KB EMUPALBUFF, bounded lists and DMA3 window ownership.
Do not diagnose an IRQ fault from source strings or an animation screenshot alone.

## Before a release / rollback

1. Explicit user release authorization and agreed remaining limitations.
2. Reviewed dependency commits reachable remotely; no dirty submodules/assets.
3. Regressions, host C, both clean builds and NDS validation; investigate warnings.
4. Required emulator/DSpico scene checks with hashes, sound/input/pacing/save
   tests; native WS vectors when asserting native timing accuracy.
5. README/TODO/current About/CI/build filenames consistent; historical records
   unchanged except factual corrections. Document unresolved defects honestly.
6. Stage named files, split tooling/docs/runtime fixes, review full diff and CI.
7. Publish only authorized binaries/docs/checksums, never private ROM/BIOS/saves.

For comparison or rollback, checkout the old release tag in a SEPARATE directory,
or use its verified published binary. Back up SD settings and saves before any
manual version comparison. Reverting a merged code change should be a reviewed
new commit, not a forced reset of shared history. Maintenance PRs remain Draft
until reviewed; they are neither automatically merged nor released.
