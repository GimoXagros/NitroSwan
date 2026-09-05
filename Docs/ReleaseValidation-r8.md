# v0.7.7-custom.r8 validation scope

## Release decision

On 2026-09-05 the user requested publication of the latest renderer-safety
changes. This release advances the r7 baseline through the A2-A4 safety work;
it is not evidence that the remaining One Piece or Digimon character-motion
symptom is completely fixed.

The exact release commit, recursive dependency revisions, final binary sizes,
SHA-256 values and release CI run are recorded in the published `BUILD_INFO.txt`
and `SHA256SUMS.txt`. The historical `v0.7.7-custom.r7` tag is not moved.

## Included safety changes

- Reviewed ARM-to-C palette, video-register, frame-complete, restore and VBlank
  paths follow the AAPCS 8-byte stack rule. A linked-object validator checks
  seven assembly symbols and ten direct/nested call paths in DS and DSi builds.
- Reset, ROM replacement and state restore quiesce renderer publication before
  restoring emulated state, rebuilding host graphics and committing a complete
  generation for a later host VBlank.
- A bounded triple-buffered descriptor owns the completed WS frame's OAM, OBJ
  tile generation, OBJ palette, BG bank and palette-raster slot together.
- 16KB OBJ seed/publication transfers remain conditional on dirty generations.
  WS-frame seed bytes and host-VBlank publication bytes are separate metrics.
- Optional ABI self-test and renderer trace builds are compile-time diagnostics;
  neither diagnostic path is enabled in the normal release binaries.

## Automated evidence

| Check | Result and provenance |
| --- | --- |
| Python regressions | PASS, 76 tests. Source/model tests are not pixel-level hardware proof. |
| Host C regressions | PASS in CI for RTC and DSpico ROM-cache vectors. |
| Repository/localization | PASS; 128 strings and 20615 non-ASCII glyphs covered. |
| DS and DSi/DSpico builds | PASS in the BlocksDS CI container. |
| Linked ARM object inspection | PASS in both profiles: 7 symbols, 10 call paths. |
| NDS packaging | PASS: executable ranges, header CRC, banner CRC, icon and six title fields. |
| Normal-build diagnostics | Trace and ABI self-test symbols are absent from release builds. |

The pre-release safety candidate passed
[CI run 33941454635](https://github.com/GimoXagros/NitroSwan/actions/runs/33941454635).
The final versioned build is rebuilt by CI from the release PR and is published
only after the same checks pass.

## Runtime evidence and limitations

| Area | Status |
| --- | --- |
| Earlier r7 DSpico result | Character corruption was substantially improved but still visible during some large motions. |
| Fresh r8 melonDS scene matrix | NOT RUN. |
| Fresh r8 DSpico gameplay, audio, input, save/load and pacing | NOT RUN. |
| Optional ARM ABI sentinel on ARM hardware | BUILT previously; NOT RUN. |
| Reset/save/load interrupt-boundary smoke | NOT RUN in emulator or hardware. |
| Native WonderSwan timing reference | NOT RUN. |
| One Piece/Digimon residual root cause | UNVERIFIED; safety defects are fixed, but no fresh paired trace proves they were the sole visual cause. |

No sprite line-142/144 timing, generic BG raster behavior, DMA3 window ownership,
1KB `EMUPALBUFF`, CPU timing, sound core or game-specific whitelist was changed
without runtime evidence. Upstream Draft PR #59 and #60 remain separate and are
not folded into this release work.

## Recommended follow-up

1. Run the normal DSi/DSpico build through the One Piece original/patched and
   Battle Spirit 1.0/1.5/Frontier movement scenes.
2. Exercise save, advance, load, repeated reset and direct ROM replacement near
   host VBlank; report graphics, sound, input and save behavior separately.
3. Run the optional ABI sentinel on DSpico.
4. If visible corruption remains, capture matched r7/r8 generation traces before
   changing sprite timing or buffer policy.
