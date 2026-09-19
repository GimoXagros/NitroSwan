# r8 stability investigation and r9 prerelease plan

## Scope and baseline

Start: 2026-09-19. Fork main and release r8 both resolve to
`20ce30634dab50fc95c369833b5f033da38fe2cd`. User hardware report: One Piece
and Digimon motion artifacts persist. This is not a confirmed timing cause.
Work branch: `fix/r8-stability-performance`; separate detached r8 baseline.
Latest user instruction authorizes an r9 prerelease. Keep the fork PR Draft,
main unchanged, previous releases intact, and upstream #59/#60 protected.

## Phases and acceptance

1. Inventory repository/dependencies/tools/assets; run baseline tests, DS/DSi
   builds, header/banner and ARM object checks. Preserve original assets read-only.
2. Audit ABI, bounds, lifecycle and IRQ publication; prove any defect with an
   executable failing case before a minimal correction and adjacent cases.
3. Exercise available emulator/runtime checks; mark unavailable scene/device
   results NOT RUN or BLOCKED, separately from host tests.
4. Audit measurement accuracy and add compile-time diagnostics where needed.
   Compare deterministic baseline/candidate operations and runtime metrics only
   where actually measured. Reject optimizations without meaningful evidence.
5. Trace affected scenes if emulator control permits; identify first divergence
   before changing sprite latch/conversion timing. Preserve video hardware bounds.
6. Run final review and validation; publish Draft PR and r9 prerelease from its
   exact tested commit, with hashes, matrix, limitations and manual DSpico steps.

## Risks and recovery

No force pushes, resets, asset edits/deletions, production CPU timing changes,
or upstream PR mutations. A test failure blocks the corresponding change from
publication until corrected. Unmeasured runtime behavior remains explicitly open.
Keep baseline binaries and separate build output names; no destructive cleanup.

## Skills and execution

Primary: exec-plan (checkpoints), nds-homebrew-build-validator (artifacts),
emulator-regression-tester (evidence matrix), graphics-vram-pipeline-debugger
(rendering). Route IRQ ordering to timing-interrupt-dma-analyzer; persistence
to save-nvram-state-validator; logs to log-analyzer as needed. V30MZ, mapper,
and bisect skills are conditional on demonstrated subsystem divergence or
repeatably good/bad endpoints, not selected merely from visible corruption.
Model/effort selection is controlled by the running client; record actual
tool-supported review configuration and do not claim unobservable switches.

## Progress

- [x] Main/release identity and private input availability checked.
- [x] Isolated candidate and detached baseline worktrees created.
- [x] Baseline verification.
- [x] Stability audit and failing-case coverage (bounded paths, not exhaustive proof).
- [x] Measurement corrections and supported optimization decisions.
- [x] Runtime/matrix/manual package (scene/device gaps explicitly retained).
- [ ] Final review, CI, Draft PR and r9 prerelease.

## Decisions and discoveries

Merged cleanup candidates remain checked out with retained build/private assets;
leave both branches and worktrees in place. No branch cleanup is necessary.
The shared local upstream/fork v0.7.7 tag conflict is historical; fetch branches
without replacing tags and fetch the requested fork release tag explicitly.

## Findings and first divergence

The linked ARM runner starts each case with identical synthetic RAM and follows
ordered instructions to the first relevant transfer. No address normalization is
applied: the scratch source is identical in both ELF tests.

| Case | r8 | candidate |
|---|---|---|
| Completed OAM 0x02e01000, scroll word 0x00010002 | DMA source 0x00010002 | DMA source 0x02e01000 |
| Completed OAM, zero scroll | legacy OAM fallback | completed OAM |
| Host refresh repeated, one BG delta | base remains 0x9999; IRQ off | base 0x1234; IRQ on |
| Same repeat with zero deltas | base remains 0x9999 | base 0x1234; IRQ still off |
| VBlank during next live OBJ palette | live buffer replaced with old colors | live bytes preserved; completed colors posted to host |
| Quiesced initial menu | zero input scans | one input scan |

These are the first divergences in synthetic renderer cases, not the first
divergence in the user's One Piece/Digimon recordings. Actual scene-aligned
sprite latch / tile / DMA evidence is still required before changing timing.
Memory.s, cpuWriteMem20, guest CPU timing, line-142/144, DMA3 window use, and
the 1KB palette allocation have not changed.

## Audit coverage and remaining risk

- Real linked ARM calls check r4-r11 preservation and balanced SP. Reviewed
  callback stack shapes are checked separately. Generic ABI sentinel is not a
  substitute for arbitrary IRQ-interleaving exploration.
- Synthetic 2bpp/4bpp packed/planar, quiesce/reset/restore and generation wrap
  use the real buffer functions. Whole-game savestate/NVRAM behavior is unchanged
  and remains a separate manual matrix. Original private data is never overwritten.
- Triple slot metadata and pending/ready ownership are retained. Unbounded
  producer schedules, BG map/bank writes, latch timing and complete pixel
  composition are not proven by this task's finite cases.
- The initial built-in review (GPT-6 Astra, xhigh) found two P2 issues: paused
  color remapping and non-root trace paths. Both were addressed; final review
  is a release gate. Its initial shell could not find Python; execution results
  here come from the main task's configured Python/ARM toolchain, not that review.

## Measurement and optimization decisions

Private machine-specific logs are under `local-reports/r8-stability/`, excluded
from Git. Before/after JSON contains actual synthetic measurements, not estimates
of real device performance. Dirty 4bpp cases publish 16,384 OBJ bytes once and
zero on repeat, both before and after. Seed/publication policy was not changed.
The r5 register substitution does not add ARM instructions to OAM pointer setup.

No new optimization was accepted: no paired hardware timing distribution exists.
Reject unconditional 16KB copying, scanline full palettes, every-write callbacks,
CPU-clock/limiter changes, game-ID special cases and speculative latch changes.
Removing the legacy OBJ palette DMA half is deferred: it would require a separate
MMIO/timing comparison across both color and mono paths. Additional repeated-frame
base/OBJ palette work in r9 is a correctness cost, not a speedup.

The diagnostic schema now distinguishes WS completion, host VBlank and cumulative
counts. It records missing latch observations honestly, detects dropped data,
segments resets, bounds each disk flush and measures host ticks only if timers
2/3 are free. See [r9 validation](ReleaseValidation-r9.md) for exact coverage and
the deliberately unmeasured metrics. Diagnostic disk I/O is unsuitable for FPS
benchmarking; release builds compile it out.

## Repository/dependency inventory

| Dependency | Preserved commit |
|---|---|
| ARMV30MZ | b989c01a73ebda2d28c81d145e80e4c9ca786587 |
| Shared | a3e101edb1d989d3b9eb175e45e49898c3de7cf6 |
| Shared/Unzip | 63769d6d58ee5600293c1e1300e49e9031858fca |
| Sphinx | 326330132dc168ca6f348688c64d66b33afda1f2 |
| WSCart | 9756f1230c262b6f98e8a3329b5172ec4dcf0d3c |
| WSCart/WSRTC | 2cf9caa1178860d2be9bfc85aa6b2624f459e298 |
| WSEEPROM | c168f3ed5ebc967b6adc2c4b41b2b502bcefd80a |

Upstream NitroSwan #59/#60 and Sphinx #4/#5, ARMV30MZ #6 were read-only checks.
No comments, ready transitions, history rewrites or dependency updates. Merged
cleanup candidates are retained because they remain checked out with local assets.

## Skill routing and next work

exec-plan maintained gates; nds-homebrew-build-validator handled toolchain and
artifact checks; emulator-regression-tester separated evidence levels;
graphics-vram-pipeline-debugger and timing-interrupt-dma-analyzer isolated host
publication; log-analyzer preserved comparison anchors and missing observations;
save-nvram-state-validator limited restore claims to tested buffer paths;
computer-use inspected a fresh melonDS boot/file browser with read-only media.
No CPU/mapper/bisect/hardware-register specialist was used: no first divergence
in those subsystems or repeatably good/bad game endpoints was established.

Prioritize DSpico scene A/B, independent latch/OAM/tile observations, full
reset/save/ROM-switch tests, then low-overhead cache/audio/save timing. Keep r8
stable until the prerelease clears these gates.
