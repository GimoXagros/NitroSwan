# RTC protocol correction — 2026-11-09

Upstream [WSRTC PR #2](https://github.com/FluBBaOfWard/WSRTC/pull/2) is closed without merging. Its longer leap-year conversion is superseded by upstream `1af2aa5`; the proposed invalid-second no-carry behavior contradicts the independent [ws-rtc-test](https://codeberg.org/asie/ws-rtc-test/src/commit/071687a0ba75f864680f5745a1a49b160ca0e076/src/main.c) expectation.

The custom fork used an older, different C calendar implementation. It saturated malformed writes and normalized every date/time field after each byte transfer. That changed invalid seconds immediately and could change fields unrelated to the write. The dependency update replaces this helper with upstream `dd7a8fe` calendar and per-register protocol handling. Seconds `E5` are masked to `65` on write, then corrected to `00` with a minute carry on the next tick.

## Integration contract

- WSRTC retains its one-argument, once-per-second `wsRtcUpdate`, status-read readiness and 20-byte ARM structure with 16 bytes of saved state. WSCart still owns the 384,000-clock divider.
- Both WSCart main and `agent/nitroswan-dspico-rom-cache-r3` advance their WSRTC pin. NitroSwan advances the latter lineage, preserving custom ROM-cache hooks.
- The unsupported C helper and tests that treated saturation as the expected result are removed. Existing Unicorn/pyelftools infrastructure executes `tools/validate_rtc_runtime.py` against both linked DS and DSi binaries through the public RTC functions.

## Validation and limits

The linked test covers register writes/readback, delayed invalid-second carry, BCD calendar boundaries, 12/24-hour handling and saved-state/ABI compatibility. It executes ARM instructions in synthetic RAM; it is not a physical RTC or cartridge timing test. Run it with:

```sh
python3 tools/validate_rtc_runtime.py build/NitroSwan-DS-0.7.7-custom.r10.elf
python3 tools/validate_rtc_runtime.py build/NitroSwan-DSi-0.7.7-custom.r10.elf
```

The usual repository/localization checks, host regressions, DS/DSi builds and existing linked renderer tests remain required. Consult the exact commit's Build workflow for execution results. Alarm/IRQ behavior is not certified or fixed by this change; upstream's remaining Alarm/IRQ work is separate.

This is a main-branch source correction, not a new release. Existing r10 tags/binaries and dated audit/release records retain their original content and validation scope.
