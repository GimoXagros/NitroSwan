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
- [ ] Baseline verification.
- [ ] Stability audit and failing-case coverage.
- [ ] Measurement corrections and supported optimization decisions.
- [ ] Runtime/matrix/manual package.
- [ ] Final review, CI, Draft PR and r9 prerelease.

## Decisions and discoveries

Merged cleanup candidates remain checked out with retained build/private assets;
leave both branches and worktrees in place. No branch cleanup is necessary.
The shared local upstream/fork v0.7.7 tag conflict is historical; fetch branches
without replacing tags and fetch the requested fork release tag explicitly.
