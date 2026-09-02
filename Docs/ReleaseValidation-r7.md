# v0.7.7-custom.r7 validation scope

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

Upstream BG-only PR #59 remains separate from the custom OBJ implementation.
CPU timing PR #60 is not changed without new timing evidence.
