#!/usr/bin/env python3
"""Linked-ARM content probes; synthetic guest RAM, not game/native validation.

The latch probe's oracle is prior-table visibility through the current visible
frame, independently of the exact hardware sprite-copy scanline. It retains
NitroSwan's existing latch event and does not equate metadata with observation.
Visibility reference: https://ws.nesdev.org/wiki/Display/Sprites
"""
import argparse
import hashlib
import json
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R12
from validate_renderer_runtime import ArmImage


def invoke(arm, symbol, r0=0):
    arm.uc.reg_write(UC_ARM_REG_R12, arm.address('sphinx0'))
    return arm.call(symbol, r0)


def complete(arm):
    arm.call('videoTileBufferFrameComplete', arm.SCRATCH)
    arm.call('videoTileBufferFrameCommit')


def packed_tile(arm, byte):
    arm.uc.mem_write(arm.address('DIRTYTILES') + 0x200, b'\x10' * 1024)
    arm.write(arm.address('DIRTYTILES') + 0x200, 0, 1)
    arm.uc.mem_write(arm.address('wsRAM') + 0x4000, bytes([byte]) * 32)
    arm.call('objTileBufferBeginFrame', 0xE0)
    arm.call('transferVRAM16Packed')


def bg_active_lifetime(path):
    arm = ArmImage(path)
    arm.call('objTileBufferReset')
    packed_tile(arm, 0x11)
    complete(arm)
    arm.call('videoTileBufferVBlank')
    active = 0x06008000 + arm.read(arm.address('wsvBgReadyTileOffset'), 2)
    initial = arm.read(active)
    packed_tile(arm, 0x22)
    complete(arm)
    packed_tile(arm, 0x33)
    changed = arm.read(active)
    obj_before = arm.read(0x06400000)
    selected_bg = arm.read(0x04000008, 2)
    arm.call('videoTileBufferVBlank')
    return {
        'case': 'bg-active-bank-survives-two-dirty-builds',
        'active_bg_address': hex(active), 'bg0cnt_before_irq': hex(selected_bg),
        'initial_word': hex(initial), 'unfinished_build_word': hex(changed),
        'obj_host_before_irq': hex(obj_before),
        'obj_host_after_irq': hex(arm.read(0x06400000)),
        'pass': changed == initial,
        'limit': 'Synthetic linked ARM content lifetime; no scanout pixels.',
    }


def latch_pairing(path, change=True, mode=0xE0, next_mode=None):
    arm = ArmImage(path)
    arm.call('objTileBufferReset')
    # Stub unrelated scroll/window and service work, never latch, conversion,
    # snapshot or publication. The actual gfxEndFrame order remains intact.
    for symbol in ('wsvCopyScrollValues', 'copyWindowValues', 'updateSlowIO',
                   'wsvUpdateIcons'):
        arm.stub(symbol)
    sphinx = arm.address('sphinx0')
    ram = arm.address('wsRAM')
    invoke(arm, 'wsVideoInit', ram)
    for symbol, value, width in (('gfxRAM', ram, 4), ('wsvVideoMode', mode, 1),
                                 ('wsvSprTblAdr', 8, 1), ('wsvSpriteCount', 1, 1)):
        arm.write(sphinx + arm.address(symbol), value, width)
    table = ram + 0x1000
    old_descriptor = 0x20200000  # x=32,y=32,tile=0
    new_descriptor = 0x40400001 if change else old_descriptor
    arm.write(table, old_descriptor)
    invoke(arm, 'latchSpritesForFrame')
    before_latch = arm.read(sphinx + arm.address('wsvSpriteRAM'))
    # Current line-zero tiles: tile zero is 1, tile one is 2. A later pose/table
    # change is deliberately independent from this already observed tile data.
    if mode == 0xE0:
        arm.uc.mem_write(ram + 0x4000, b'\x11' * 32 + b'\x22' * 32)
    elif mode == 0xC0:
        arm.uc.mem_write(ram + 0x4000, b'\xff\x00\x00\x00' * 8 + b'\x00\xff\x00\x00' * 8)
    else:
        arm.uc.mem_write(ram + 0x2000, b'\xff\x00' * 8 + b'\x00\xff' * 8)
    invoke(arm, 'newFrame')
    arm.write(table, new_descriptor)
    invoke(arm, 'latchSpritesForFrame')
    after_latch = arm.read(sphinx + arm.address('wsvSpriteRAM'))
    invoke(arm, 'gfxEndFrame')
    oam_source = arm.call('videoTileBufferVBlank')
    oam_attr01 = arm.read(oam_source)
    actual_tile = arm.read(oam_source + 4, 2) & 0x1FF
    expected_tile = old_descriptor & 0x1FF
    result = {
        'case': 'completed-oam-retains-visible-frame-latch' if change else 'unchanged-latch-control',
        'guest_table_address': hex(table),
        'latch_buffer_address': hex(sphinx + arm.address('wsvSpriteRAM')),
        'observed_previous_latch_word': hex(before_latch),
        'observed_current_latch_word': hex(after_latch),
        'completed_oam_source': hex(oam_source), 'oam_attr01': hex(oam_attr01),
        'expected_tile': expected_tile, 'actual_tile': actual_tile,
        'actual_host_tile_word': hex(arm.read(0x06400000 + actual_tile * 32)),
        'pass': actual_tile == expected_tile,
        'limit': ('Synthetic OAM content only; decoded 2bpp bytes are tested by validate_2bpp_runtime.py.'
                  if mode & 0xC0 != 0xC0 else
                  'Synthetic latch and decoded tile content; not a proven game-scene cause.'),
    }
    if mode & 0xC0 == 0xC0:
        result['pass'] &= arm.read(0x06400000 + actual_tile * 32) == 0x11111111
    # A second real begin/latch/end trip must use B immediately, not A again.
    if next_mode is not None:
        arm.write(sphinx + arm.address('wsvVideoMode'), next_mode, 1)
    invoke(arm, 'newFrame')
    third_descriptor = 0x60600002 if change else old_descriptor
    arm.write(table, third_descriptor)
    invoke(arm, 'latchSpritesForFrame')
    invoke(arm, 'gfxEndFrame')
    # Begin a third guest frame before host refresh. Its OAM preparation must
    # not overwrite the ready/completed slot from the second guest frame.
    invoke(arm, 'newFrame')
    second = arm.call('videoTileBufferVBlank')
    second_tile = arm.read(second + 4, 2) & 0x1FF
    result.update(mode=hex(mode), second_actual_tile=second_tile,
                  second_expected_tile=new_descriptor & 0x1FF)
    result['pass'] &= second_tile == (new_descriptor & 0x1FF)
    if next_mode is not None:
        result['next_mode'] = hex(next_mode)
    repeated = arm.call('videoTileBufferVBlank')
    result['repeat_preserved'] = repeated == second and (arm.read(repeated + 4, 2) & 0x1FF) == second_tile
    result['pass'] &= result['repeat_preserved']
    # Direct refresh is a separate explicit live rebuild entry. In current GUI
    # it is called after power-off, not from the normal line-zero pipeline.
    refresh_tiles = []
    for _ in range(4):
        invoke(arm, 'gfxRefresh')
        refreshed = arm.call('videoTileBufferVBlank')
        refresh_tiles.append(arm.read(refreshed + 4, 2) & 0x1FF)
    result['refresh_tiles'] = refresh_tiles
    result['refresh_preserved'] = refresh_tiles == [third_descriptor & 0x1FF] * 4
    result['pass'] &= result['refresh_preserved']
    arm.call('objTileBufferReset')
    invoke(arm, 'newFrame')
    invoke(arm, 'gfxEndFrame')
    reset_oam = arm.call('videoTileBufferVBlank')
    result['reset_current_latch_tile'] = arm.read(reset_oam + 4, 2) & 0x1FF
    result['pass'] &= result['reset_current_latch_tile'] == (third_descriptor & 0x1FF)
    invoke(arm, 'gfxRebuildRendererState')
    rebuilt = arm.call('videoTileBufferVBlank')
    result['rebuild_current_latch_tile'] = arm.read(rebuilt + 4, 2) & 0x1FF
    result['pass'] &= result['rebuild_current_latch_tile'] == (third_descriptor & 0x1FF)
    return result


def restored_oam_survives_resume(path, start_line):
    """Resume synthetic restored video state through the real scanline scheduler.

    This is not a serialized game-state roundtrip. At line 143 the earlier
    visible-frame latch is no longer available in saved state, so the oracle is
    continuity with the immediate rebuilt image, not exact native partial-frame
    reconstruction.
    """
    arm = ArmImage(path)
    arm.call('objTileBufferReset')
    sphinx = arm.address('sphinx0')
    ram = arm.address('wsRAM')
    invoke(arm, 'wsVideoInit', ram)
    for symbol in ('wsvCopyScrollValues', 'copyWindowValues', 'updateSlowIO',
                   'wsvUpdateIcons', 'soundUpdate', 'setInterruptPins',
                   'dispCnt', 'windowCnt', 'scrollCnt'):
        arm.stub(symbol)
    next_change = 143 if start_line < 143 else 144
    callback_offset = 12 if next_change == 143 else 20
    fields = (('wsvVideoMode', 0xE0, 1), ('wsvSprTblAdr', 8, 1),
              ('wsvSpriteCount', 1, 1), ('scanline', start_line, 4),
              ('nextLineChange', next_change, 4),
              ('lineState', arm.address('lineStateTable') + callback_offset, 4))
    for symbol, value, width in fields:
        arm.write(sphinx + arm.address(symbol), value, width)
    # Poison each recycled slot distinctly so a stale temp cannot accidentally
    # equal the freshly rebuilt sprite, even with otherwise zero synthetic RAM.
    for index in range(1, 4):
        arm.write(arm.address(f'OAM_BUFFER{index}') + 4, 10 + index, 2)
    arm.write(ram + 0x1000, 0x20200007)
    invoke(arm, 'latchSpritesForFrame')
    arm.call('objTileBufferCompleteStateRestore', 0xE0)
    invoke(arm, 'gfxRebuildRendererState')
    rebuilt = arm.call('videoTileBufferVBlank')
    rebuilt_tile = arm.read(rebuilt + 4, 2) & 0x1FF
    frame_before = arm.read(arm.address('frameTotal'))
    begin_calls = []
    entry = arm.address('newFrame')
    arm.uc.hook_add(UC_HOOK_CODE, lambda uc, pc, size, data: begin_calls.append(pc),
                    begin=entry, end=entry)
    arm.write(ram + 0x1000, 0x40400008)
    scanlines = []
    for _ in range(144 - start_line):
        invoke(arm, 'wsvDoScanline')
        scanlines.append(arm.read(sphinx + arm.address('scanline')))
    completed = arm.call('videoTileBufferVBlank')
    completed_tile = arm.read(completed + 4, 2) & 0x1FF
    latch_word = arm.read(sphinx + arm.address('wsvSpriteRAM'))
    expected_latch = 0x40400008 if start_line < 143 else 0x20200007
    return {
        'case': f'restored-oam-resume-line-{start_line}',
        'rebuilt_oam_source': hex(rebuilt), 'completed_oam_source': hex(completed),
        'rebuilt_tile': rebuilt_tile, 'completed_tile': completed_tile,
        'expected_tile': 7, 'observed_scanlines': scanlines,
        'observed_latch_word': hex(latch_word), 'new_frame_calls': len(begin_calls),
        'pass': rebuilt_tile == completed_tile == 7 and not begin_calls
                and latch_word == expected_latch
                and arm.read(arm.address('frameTotal')) == frame_before + 1,
        'limit': ('Synthetic post-load renderer/scheduler, not game save roundtrip; '
                  'line-143 oracle is rebuilt-image continuity, not native partial-frame reconstruction.'),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('elf', type=Path)
    parser.add_argument('--include-known-bg', action='store_true',
                        help='Include independent unresolved BG lifetime case (expected FAIL).')
    args = parser.parse_args()
    results = [latch_pairing(args.elf, mode=mode) for mode in (0, 0x80, 0xC0, 0xE0)]
    results += [latch_pairing(args.elf, False)]
    results += [latch_pairing(args.elf, mode=before, next_mode=after)
                for before, after in ((0, 0xC0), (0xC0, 0xE0), (0xE0, 0x80))]
    results += [restored_oam_survives_resume(args.elf, line) for line in (141, 143)]
    if args.include_known_bg:
        results.append(bg_active_lifetime(args.elf))
    print(json.dumps({'elf': str(args.elf),
                      'sha256': hashlib.sha256(args.elf.read_bytes()).hexdigest(),
                      'results': results}, indent=2))
    return 0 if all(result['pass'] for result in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
