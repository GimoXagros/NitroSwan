# v0.7.7-custom.r7 validation scope

This is the historical 2026-09-02 release record, not the latest development
test report. Later maintenance findings belong in [BaselineAudit-r7.md](BaselineAudit-r7.md).

- Release/main commit and dereferenced tag `v0.7.7-custom.r7`:
  `06178156341d70fd876174272d04f5cb5d440a2b` (rechecked 2026-09-03).
- Build source: `e31a53b8cd1b8197cabec15df9278eaff7adbcfc`, with an identical
  tracked tree to the merge commit above.
- Sphinx gitlink: `97bf9fe4fdbeb0f761b22fe8e1fa68b5670a364e`.
- Release CI: [pre-merge success](https://github.com/GimoXagros/NitroSwan/actions/runs/33624417402)
  and [main success](https://github.com/GimoXagros/NitroSwan/actions/runs/33624531321).
- Published DS SHA-256: `6d663ec181509eeb99dbdf9aed47bf345e5b6d3ec822d136310333f2d2c35e9d`.
- Published DSi SHA-256: `d356f54e1ad01eb323b915efc95d9186533ecd029d18b21266df6eece2c82606`.

No post-release maintenance changes or new tests are retroactively credited to r7.

## Release decision

On 2026-09-02 the user approved release after DSpico hardware testing, while
explicitly reporting some remaining character-motion corruption. This is a
partial improvement release. Do not describe all character graphics, animation
latency or hardware timing as fully fixed.

The renderer is the internal WSC-VideoCore-r8-test implementation:

- NitroSwan renderer commit: `869e81f`
- Sphinx commit: `97bf9fe` (see the pinned submodule for the full revision)
- DS test SHA-256: `1160405efdd6d2f04aa1a4708a265f7bddec02a65c3a848e9555b8018dbd851d`
- DSi test SHA-256: `945cd909967318b104811957d83ed7be87a5372fa23a8f8cd1bcbe6b1b91683a`

Release packaging changes documentation, the About version string and CI/test
configuration, not the r8 renderer. Final release checksums and full source
revisions are included in the release's BUILD_INFO.txt and SHA256SUMS.txt.

## Evidence and limits

| Check | Result and provenance |
| --- | --- |
| Background comparison | User reported backgrounds correct against Oswan after r7-test. The same BG renderer is retained in r8-test and this release. |
| Rockman & Forte background | User reported the issue resolved. No claim of whole-game completion or root-cause attribution. |
| Character motion on DSpico | User tested r8-test: substantially improved from the initial build, but some corruption remains. |
| Earlier melonDS smoke checks | Development records include One Piece original/patched, Battle Spirit 1.0/1.5/Frontier, Final Lap Special and Digimon Anode/Cathode boot/intro checks. These are not exhaustive gameplay passes for the final release. |
| Python source/model regressions | 48 tests pass on r8-test; these do not prove DS scanout/interrupt timing or pixel correctness. Release runner also executes the RTC and ROM-cache C tests. |
| DS and DSi builds | Both r8-test builds compiled/linked successfully; release files are rebuilt with the corrected About version. Existing unused-variable/function and old-style crc32 warnings remain. |
| Performance, sound, input, save | No hot-path CPU/audio/save changes in the release packaging. Earlier development checks are not a fresh exhaustive final-build performance or NVRAM certification. |
| Native WonderSwan hardware | No new cycle-accurate reference capture performed for this release. DSpico testing is not a native WonderSwan timing reference. |

## Follow-up

1. Preserve this release and its reference recordings.
2. Capture paired OAM, decoded tile, sprite-latch, palette and host VBlank
   generations in the exact remaining One Piece/Digimon scenes.
3. Check publication atomicity, partial-frame ownership, sprite visibility and
   animation latency against a reference before choosing another renderer change.
4. Keep the working BG path and Rockman & Forte regression scene unchanged.
5. Add VBlank copy costs to performance accounting: the current
   `objBytesCopiedFrame` metric counts snapshot seeding, not every publication
   copy. Do not use it as a total-bandwidth measurement.
   It resets at each emulated WS frame and is 0 or 16384; its maximum is a
   session high-water mark, not an aggregate. A host VBlank is a different
   boundary. Separate seed/publication counters and their aggregation policy
   remain follow-up work; no total counter was validated in the release.

Upstream BG-only PR #59 remains separate from the custom OBJ implementation.
CPU timing PR #60 is not changed without new timing evidence.
