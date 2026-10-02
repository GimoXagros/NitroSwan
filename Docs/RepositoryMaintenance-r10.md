# r10 repository maintenance — 2026-10-02

## Purpose and scope
Consolidate repository navigation, merged branches and contributor attribution
around stable v0.7.7-custom.r10. Documentation/metadata only: no emulator source,
gitlinks, binaries, release tag targets, private files or author history changes.

## Confirmed baseline
- Default main and r10 release commit: `9a0f46e5cc615a70676437d5ade297879331cc23`.
- GitHub latest stable: v0.7.7-custom.r10; r9 remains a historical prerelease.
- Fork PRs #9, #10, #11 and #12 are MERGED; all four heads are main ancestors.
- Active upstream PRs #59 and #60 still require their independent minimal heads.
- All existing version tags and AccuratePC are historical references, not
  redundant disposable branch names. Preserve them and all release assets.

## Phases and acceptance
- [x] Inventory remote branches, tags, releases, contributors and cross-repo PRs.
- [x] Confirm merged ancestry; inspect local status and stash without deleting work.
- [x] Consolidate README/TODO, record credits and normalize author aliases.
- [x] Validate document links, repository checks and documentation-only diff.
- [x] Publish [maintenance PR #13](https://github.com/GimoXagros/NitroSwan/pull/13)
  and retire the four merged remote heads below. PR checks/state are the live
  source of truth for CI completion and merge; merge only after CI succeeds.
- [x] Verify latest release, unchanged tag/asset identities and retained PR heads.

## Branch retention and recovery
Keep `main`, `agent/todo2-bg-palette` (upstream #59) and
`agent/opcode-fetch-waitstate-upstream` (upstream #60).
Do not merge these intentionally minimal upstream branches into custom main.

These merged remote branch refs were removed on 2026-10-02; commits remain
reachable through main and merged PRs. Local branches/worktrees are untouched.

| Branch | Merged PR | Recovery commit |
| --- | --- | --- |
| chore/r7-baseline-audit | #9 | 19113ebdaccbf7bc137afc65a61910ab8fab8cc5 |
| fix/r7-renderer-safety-obj-coherency | #10 | 06bea89aae504f7be21af71323f8a3bd058b8568 |
| fix/r8-stability-performance | #11 | dffa5d6ac20c99bb27502a0a3d565c1189705ecc |
| fix/r9-character-motion | #12 | 02c283ad9ffbca55a879117ab07a307dc4353a06 |

Recovery: `git push <fork-remote> <recovery-commit>:refs/heads/<branch>`.
Check remote identity first. A concurrent head change cancels deletion; deletion
must be guarded by the observed SHA. Do not remove submodule branches.

## Release and contributor policy
Keep r10 latest; mark older releases as historical/superseded in their notes,
without changing their original prerelease classification, tag targets or files.
Do not silently replace ZIP contents when only main documentation changes.
Latest guidance is in main; downloadable archives remain their release snapshots.

See [Contributors](../CONTRIBUTORS.md). GitHub's generated contributor statistics
are not a hand-editable list; .mailmap does not rewrite history or promise UI counts.

## Risks and remaining work
Validation: repository hygiene (205 entries), localization (128 entries), changed
document relative links and whitespace checks passed. All 36 tag refs and 55
release assets across 11 releases retain their identities, sizes and digests.
The four branch deletions used exact-head leases; both upstream PR heads remain.
GitHub About now identifies the custom fork and links to the latest release.

No runtime rebuild or new hardware certification is appropriate for a docs-only
maintenance change. Existing r10 limitations remain in [TODO](../NitroSwan_todo.txt).
Old validation documents retain their dated evidence; do not relabel them as new passes.
