# NitroSwan V0.7.7-custom.r6

<img align="right" width="220" src="./logo.png" alt="The WonderSwan logo" />

This is a Bandai WonderSwan (Color/Crystal) & Benesse PocketChallenge V2
emulator for the Nintendo DS(i)/3DS. This custom release adds an optimized
Nintendo 3DS DSpico/DSi profile, English/Japanese/Korean menus, multilingual
filenames, per-game RAM cheats, and accuracy fixes based on the upstream 0.7.7
core.

> **One Piece modified-ROM compatibility:** custom.r6 replaces the original-ROM
> checksum gate with stable publisher/color/product/revision identity. The
> Japanese original and Korean-patched ROM are both DSpico hardware-verified.

## 0.7.7-custom.r6 주요 기능

- Nintendo 3DS의 DSpico/Pico Loader 환경에서 DSi 134 MHz CPU를 요청하고,
  불안정한 75 Hz 화면 주사율 변경을 차단해 60 Hz 프레임 변환 경로를 사용합니다.
- 메뉴 언어는 `Options > Machine > Language`에서 영어/일본어/한국어로
  변경할 수 있으며 기존 설정 파일과 호환됩니다.
- UTF-8 및 기존 CP949 한글 파일명을 지원합니다. 한글/일본어 글꼴은 원본
  영문 메뉴와 같은 흰색-회색 계조 및 검은색 그림자 스타일로 표시됩니다.
- 게임별 `.cht` RAM 치트를 지원합니다. 자세한 형식은 아래 `Cheats` 절을
  참고하십시오.
- RTC 날짜 보정·윤년·월말 처리와 흑백 기종의 16KB RAM 범위를 수정했습니다.
- DSpico 디버거 RAM의 대용량 ROM은 그대로 보관하고, 현재 표시되는 64KB
  ROM 뱅크만 DS 메인 RAM에 복사하는 프로젝트 전용 캐시를 사용합니다. 이
  방식은 NDS_Shared와 BlocksDS의 MPU 및 `memCached()`/`memUncached()` 구성을
  변경하지 않습니다.
- Pico Launcher가 전달하는 FAT 장치 경로를 유지하고 ROM을 제한된 크기의
  블록으로 읽어, 최초 직접 실행 시 로딩 화면에서 멈추는 문제를 수정했습니다.
- 직접 실행한 ROM도 `/nitroswan`에 NVRAM을 저장합니다. 자동 저장은 기본으로
  켜져 있으며, 기존 raw `.sav` 파일도 보조 입력 형식으로 불러올 수 있습니다.
- 화면이 나오지 않거나 사운드가 끊기는 회귀를 막기 위해 영상·사운드·CPU
  실시간 경로는 실기에서 검증된 `0.7.7-custom` 동작으로 복원했습니다.
- 알려진 게임 전용 CPU idle-loop 속도핵을 다시 활성화했습니다. 기본값은
  꺼짐이며 `Options > Machine > Cpu Speed Hacks`에서 켤 수 있습니다.
- `From TV Animation One Piece - Grand Battle Swan Colosseum`의 캐릭터 타일
  깨짐은 게임 전용 4bpp OBJ 이중 버퍼와 sprite latch로 수정했습니다. r6는
  WonderSwan background-color register와 palette RAM의 실제 write를 bounded
  event로 기록하고 DS의 `BG_PALETTE[0]` backdrop으로 재생해 전투 하늘
  그라데이션도 복원합니다.
  두 경로 모두 bounded triple buffer를 사용하며 OBJ 팔레트 raster와 DMA3는
  사용하지 않으므로 기존 HBlank 창 처리를 유지합니다. 전투 하늘과 캐릭터
  그래픽은 일본어 원본 ROM의 melonDS 및 DSpico 실기에서 정상 동작을
  확인했습니다. r6에서는 checksum 의존성을 제거했으며 일본어 원본과 한글패치
  ROM 모두 DSpico 실기에서 하늘·캐릭터·사운드·입력·속도가 정상입니다.
- `Mahjong Touryuumon`이 사용하는 `$A0` cartridge ROM opcode/immediate-fetch
  waitstate를 반영했습니다. 속도·사운드·입력은 DSpico 실기에서 정상 동작을
  확인했습니다.

### Which build should I use? / 빌드 선택

- `NitroSwan-DSi-0.7.7-custom.r6.nds`: DSi 모드의 3DS+DSpico/Pico Loader 및
  DSi용 권장 빌드입니다. 호환성을 위해 주사율 변경은 항상 꺼집니다.
- `NitroSwan-DS-0.7.7-custom.r6.nds`: DS/DS Lite 및 일반 DS-mode
  플래시카트용 빌드입니다.

## How to use

1. On first launch NitroSwan creates `/nitroswan` in the root of the SD card
 and writes a default `settings.cfg` there. Existing `nitroswan` folders in the
 current directory or under `/data` remain compatible. A FAT hidden attribute
 on the folder does not prevent settings, state, EEPROM, or SRAM access.
2. Now put game/bios files into a folder where you have (WonderSwan) roms, max
 768 files per folder. UTF-8 and legacy Korean CP949 filenames are supported
 (the filename buffer accepts up to 1023 bytes). You can use
 zip-files (as long as they use the deflate compression). CAUTION! Games that
 require SLOT-2 RAM can not be used with zip-files!
3. Depending on your flashcart you might have to DLDI patch the emulator.

The save files should be compatible with most other WonderSwan emulators.

When the emulator starts, you can either press L+R or tap on the screen to open
 up the menu. Now you can use the cross or touchscreen to navigate the menus, A
 or double tap to select an option, B or the top of the screen to go back a
 step.

To select between the tabs use R & L or the touchscreen.

Hold Start while starting a game to enter the boot rom settings, the internal
 EEPROM is saved when saving settings.

Since the DS/DS Lite only has 4MB of RAM you will need a SLOT-2/GBA cart with
 RAM to play games larger than 2MB.

## Menu

### File

* Load Game: Select a game to load.
* Load State: Load a previously saved state of the currently running game.
* Save State: Save a state of the currently running game.
* Load NVRAM: Load non volatile ram (EEPROM/SRAM) for the currently running game.
* Save NVRAM: Save non volatile ram (EEPROM/SRAM) for the currently running game.
  NitroSwan writes native `.ram` or `.eeprom` files in `/nitroswan`; raw `.sav`
  files of the expected cartridge size are also accepted when loading.
* Load Patch: Apply an IPS patch to the currectly loaded rom.
* Cheats: Enable or disable cheats loaded from the current game's `.cht` file.
* Save Settings: Save the current settings (and internal EEPROM).
* Reset Game: Reset the currently running game.

### Options

* Controller:
  * Autofire: Select if you want autofire.
  * Swap A/B: Swap which NDS button is mapped to which WS button.
  * Alternate layout: See Controls.
* Display:
  * Gamma: Lets you change the gamma ("brightness").
  * Contrast: Lets you change the contrast.
  * B&W Palette: Here you can select the palette for B & W games.
  * Border: Choose what to show outside the WS screen.
* Machine:
  * Machine: Select the emulated machine.
  * Select WS Bios: Load a real WS Bios.
  * Select WS Color Bios: Load a real WS Color Bios.
  * Select WS Crystal Bios: Load a real WS Crystal Bios.
  * Import Internal EEPROM: Load a special internal EEPROM.
  * Clear Internal EEPROM: Reset internal EEPROM.
  * Headphones: Select whether heaphones are connected or not.
  * Cpu speed hacks: Allow speed hacks.
  * Language: Select English, Japanese, or Korean menus.
* Settings:
  * Speed: Switch between speed modes.
    * Normal: Game runs at its normal speed.
    * 200%: Game can run up to double speed.
    * Max: Games can run up to 4 times normal speed.
    * 50%: Game runs at half speed.
  * Allow Refresh Change: Allow the Wonderswan to change NDS refresh rate.
  * Autoload State: Toggle Savestate autoloading. Automagically load the savestate associated with the selected game.
  * Autoload NVRAM: Toggle EEPROM/SRAM autoloading. Automagically load the EEPROM/SRAM associated with the selected game.
  * Autosave NVRAM: Save EEPROM/SRAM when opening the menu or quitting. Enabled by default.
  * Autosave Settings: This will save settings when leaving menu if any changes are made.
  * Autopause Game: Toggle if the game should pause when opening the menu.
  * Powersave 2nd Screen: If graphics/light should be turned off for the GUI screen when menu is not active.
  * Emulator on Bottom: Select if top or bottom screen should be used for emulator, when menu is active emulator screen is allways on top.
  * Autosleep: Doesn't work.
* WonderWitch: Tools for interacting with a WonderWitch.
  * See WonderWitch.md for more information.
* BootFriend: For uploading/downloading files with BootFriend.
* Debug:
  * Debug Output: Show FPS and logged text.
  * Disable Foreground: Turn on/off foreground rendering.
  * Disable Background: Turn on/off background rendering.
  * Disable Sprites: Turn on/off sprite rendering.
  * Disable Windows: Turn on/off window effects.
  * Step Frame: Emulate one frame.

### About

Some info about the emulator and game...

## Cheats

Put a text file beside the game with the same basename and a `.cht` extension.
For example, `MyGame.wsc` uses `MyGame.cht`. The file is read automatically
after the game loads. Press A in `File > Cheats` to toggle an entry; the enabled
state is saved immediately.

```text
# Address:value enabled description
01234:7F 1 Infinite energy
01235FF 0 Disabled example

# Conditional: write value only when the current byte equals compare
01236?10:20 1 Conditional example
```

Addresses and values are hexadecimal. For stability, this release accepts only
the WonderSwan internal RAM/current SRAM range `00000`-`1FFFF`, up to 64 entries,
and one-byte writes. Blank lines and lines beginning with `#` or `;` are ignored.
Codes without an enabled flag are loaded disabled.

## Build

BlocksDS is required. Run the regression suite first, then build:

```sh
python3 tools/run_core_regressions.py
make NAME=NitroSwan-DS-0.7.7-custom.r6
```

The DSi/DSpico build is:

```sh
make NAME=NitroSwan-DSi-0.7.7-custom.r6 DSPICO_3DS_BUILD=1 \
  SPECS="$BLOCKSDS/sys/crts/dsi_arm9.specs"
```

The r2 DSi base was verified with Pico Launcher/DSpico on Nintendo 3DS for
direct ROM launch, gameplay, menu operation, automatic folder/config creation,
NVRAM save creation, exit-time saving and save reload. The r3 bank cache is
covered by host regressions and complete DS/DSi builds. The One Piece combat
character and battle-sky fixes were verified for both the Japanese original and
Korean-patched ROM on DSpico hardware; graphics, speed, sound and input remained
normal. Mahjong Touryuumon's speed, sound and input were also verified on DSpico
hardware.

Run `python3 tools/validate_localization.py` before building. It verifies the
translation table, binary font structure, duplicate keys, and complete
Japanese/Korean glyph coverage.

## Controls

### WonderSwan

```text
Start is mapped to WS Start.
Select is mapped to WS Sound.
In horizontal games the d-pad is mapped to WS X1-X4. A & B buttons are mapped to WS A & B.
Holding L or R maps the dpad to WS Y1-Y4.

In vertical games the d-pad is mapped to WS Y1-Y4. A, B, X & Y are mapped to WS X1-X4.

In alternate layout it is the same as normal horizontal, except L, R, X & Y are
mapped to WS Y1-Y4. To open the menu use L+Select.
```

### Pocket Challenge V2

```text
Dpad is mapped to up, down, left & right.
L is mapped to Escape.
R & X is mapped to Voice/View.
A is mapped to Clear.
B is mapped to Circle.
Y is mapped to Pass.
```

## Games

Known limitations in this custom release:

* Beatmania: Game is too large even for the DSi. Can be used with a 16MB SLOT-2 card or on 3DS.
* Chou Denki Card Game: You need to initialize NVRAM, the last item on the first page (初期化).
* The standalone opcode-fetch timing ROM still needs WonderSwan hardware vectors;
  Mahjong Touryuumon itself is verified on DSpico.
* Dicing Knight: sprite priority can place shadows in front of the player.

## Accuracy

I've made a few test programs for the WonderSwan to be able to really make sure
 it is as accurate as possible.

* [WSCPUTest](https://github.com/FluBBaOfWard/WSCpuTest) - Tests functions of the NEC V30MZ CPU instructions.
* [WSTimingTest](https://github.com/FluBBaOfWard/WSTimingTest) - Tests timing of the NEC V30MZ CPU instruction.
* [WSHWTest](https://github.com/FluBBaOfWard/WSHWTest) - Tests other HW of the WS SOC.
* [KarnakTest](https://github.com/FluBBaOfWard/KarnakTest) - Tests the Karnak mapper in certain cartridges.

Other test programs I have used to get better accuracy.

* [WS-Test-Suite](https://github.com/asiekierka/ws-test-suite) - Lots of small tests.
* [RTC Test](https://forums.nesdev.org/viewtopic.php?t=21513) Tests the RTC in certain cartridges.

## Credits

```text
Huge thanks to Loopy for the incredible PocketNES, without it this emu would probably never have been made.
Thanks to:
asie for info and inspiration. https://ws.nesdev.org/wiki/WSdev_Wiki
Ed Mandy (Flavor) for WonderSwan info & flashcart. https://www.flashmasta.com
Koyote for WonderSwan info.
Alex Marshall (trap15) for WonderSwan info. http://daifukkat.su/docs/wsman/
Guy Perfect for WonderSwan info http://perfectkiosk.net/stsws.html
Godzil for the boot rom stubs. https://github.com/Godzil/NewOswan
lidnariq for RTC info.
plasturion for some BnW palettes.
Dwedit for help and inspiration with a lot of things. https://www.dwedit.org
```

Fredrik Ahlström

<https://bsky.app/profile/therealflubba.bsky.social>

<https://www.github.com/FluBBaOfWard>

X/Twitter @TheRealFluBBa
