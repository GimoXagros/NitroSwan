# DSpico r7 renderer-safety manual test

These files are development tests, not a release. Keep the existing r7 release
installed as the comparison build. Do not distribute ROM, BIOS, save or trace
files.

1. Run `NitroSwan-DSi-r7-abi-selftest-final.nds` once through DSpico. Normal
   startup means the ABI sentinel returned zero. If it stops on a renderer ABI
   error, record the eight-digit code and stop testing this candidate.
2. Run `NitroSwan-DSi-r7-safety-test.nds`. Check direct Pico Loader launch,
   normal menu launch, reset immediately before VBlank, save state, advance,
   load state, repeated load/reset and ROM replacement. Confirm that the first
   completed post-restore frame appears and that no stale pre-restore frame,
   hang or blank screen is published.
3. Check original and patched One Piece: enter battle, fast left/right movement,
   large attacks, battle exit and re-entry. Record character corruption,
   animation delay, BG, UI, sound, input and pacing separately.
4. Repeat movement/attack/BG/UI checks for Battle Spirit 1.0, 1.5 and Frontier.
   Then smoke-test normal WSC 4bpp controls, color 2bpp, mono WS, Rockman &
   Forte BG and Mahjong Touryuumon speed/sound/input/save.
5. If corruption remains, repeat the exact input with
   `NitroSwan-DSi-r7-video-trace-final.nds`. Exit normally so buffered rows are
   flushed. Copy `/nitroswan/renderer-trace-r7-safety.csv` from the SD card to
   the repository's ignored `local-reports` folder and run:

       python tools/analyze_renderer_trace.py local-reports/renderer-trace-r7-safety.csv

Report PASS only for scenes actually observed. The trace build intentionally
adds logging overhead and is not a performance candidate. The normal safety
build contains neither trace nor ABI-self-test code.
