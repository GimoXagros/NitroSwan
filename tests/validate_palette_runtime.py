#!/usr/bin/env python3
"""Linked ARM palette-mode regression, synthetic guest state and host MMIO.

The real paletteTxAll conversion is the independent legacy-palette oracle.
This does not emulate scanout or certify game scenes on physical hardware.
"""
import argparse
import hashlib
import json
from pathlib import Path

from arm_image import ArmImage
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_PC, UC_ARM_REG_LR


def mode(arm, value):
    arm.write(arm.address('sphinx0') + arm.address('wsvVideoMode'), value, 1)


def setup(path, soc, video_mode):
    arm = ArmImage(path)
    arm.set('gSOC', soc, 1)
    mode(arm, video_mode)
    for index in range(4096):
        arm.write(arm.address('MAPPED_RGB') + index * 2, 0x1000 + index, 2)
    for index in range(16):
        arm.write(arm.address('MAPPED_BNW') + index * 2, 0x600 + index, 2)
    arm.write(arm.address('sphinx0') + arm.address('wsvColor01'), 0x76543210)
    for index in range(16):
        arm.write(arm.address('sphinx0') + arm.address('wsvPalette0') + index * 2, 0x3210, 2)
    for index in range(256):
        arm.write(arm.SCRATCH + 0x3000 + index * 2, index, 2)
    arm.call('paletteRasterConfigure', arm.SCRATCH + 0x2000)
    return arm


def legacy_palette(arm):
    # Poison unused entries too: replay may not write them in unsupported modes.
    arm.uc.mem_write(arm.address('EMUPALBUFF'), b'\xAA\x55' * 512)
    arm.call('paletteTxAll')
    return bytes(arm.uc.mem_read(arm.address('EMUPALBUFF'), 256))


def complete(arm):
    arm.call('paletteRasterFrameComplete')


def publish(arm, expected):
    # Model only the legacy BG palette DMA contents, not bus/timing behavior.
    arm.uc.mem_write(0x05000000, expected)
    arm.call('paletteRasterVBlank')
    return bytes(arm.uc.mem_read(0x05000000, 256)) == expected


def mode_case(path, soc, video_mode):
    arm = setup(path, soc, video_mode)
    expected = legacy_palette(arm)
    complete(arm)
    first = publish(arm, expected)
    repeat = publish(arm, expected)
    # Exercise suspend/reconfigure with the same emulated mode. The old ELF
    # lacks suspend; configure(NULL) supplies its existing disable operation.
    arm.call('paletteRasterSuspend') if 'paletteRasterSuspend' in arm.symbols else arm.call('paletteRasterConfigure', 0)
    arm.call('paletteRasterConfigure', arm.SCRATCH + 0x2000)
    complete(arm)
    restore = publish(arm, expected)
    return {'case': f'soc-{soc}-mode-{video_mode:02x}',
            'first_preserved': first, 'repeat_preserved': repeat,
            'restore_preserved': restore, 'pass': first and repeat and restore}


def event(arm, color=0x234):
    arm.write(arm.address('sphinx0') + arm.address('scanline'), 5)
    arm.write(arm.SCRATCH + 0x3002, color, 2)
    arm.call('paletteRasterCapturePaletteWrite', 0xFE02)


def live_next_mode(path):
    arm = setup(path, 2, 0xC0)
    base = legacy_palette(arm)
    event(arm)
    complete(arm)
    # The next unfinished guest frame must not change the completed frame tag.
    mode(arm, 0)
    first = publish(arm, base)
    armed = bool(arm.read(0x04000004, 2) & 0x20)
    arm.call('paletteRasterVCountIrq')
    delta = arm.read(0x05000002, 2)
    repeat = publish(arm, base)
    arm.call('paletteRasterVCountIrq')
    return {'case': 'completed-color-survives-next-live-mono',
            'delta': hex(delta), 'pass': first and repeat and armed
            and delta == 0x1234 and arm.read(0x05000002, 2) == 0x1234}


def transitions(path, intermediate):
    arm = setup(path, 2, 0xC0)
    event(arm)
    complete(arm)
    arm.call('paletteRasterVBlank')
    # A non-4bpp completed frame MUST replace, rather than skip, the old active.
    mode(arm, intermediate)
    event(arm, 0x345)
    expected = legacy_palette(arm)
    complete(arm)
    first = publish(arm, expected)
    irq_off = not (arm.read(0x04000004, 2) & 0x20)
    arm.call('paletteRasterVCountIrq')  # stale IRQ must not replay old events
    stale_safe = bytes(arm.uc.mem_read(0x05000000, 256)) == expected
    repeat = publish(arm, expected)
    # Capture began unsupported, then enters 4bpp: fall back until next capture.
    mode(arm, 0xE0)
    event(arm, 0x456)
    expected_color = legacy_palette(arm)
    complete(arm)
    mixed = publish(arm, expected_color)
    # A later complete 4bpp capture must resume base + delta replay.
    color_base = legacy_palette(arm)
    event(arm, 0x567)
    complete(arm)
    resumed = publish(arm, color_base)
    arm.call('paletteRasterVCountIrq')
    return {'case': f'color-to-{intermediate:02x}-back-to-color',
            'legacy_preserved': first and repeat and stale_safe,
            'irq_off': irq_off, 'mixed_frame_fallback': mixed,
            'color_replay_resumed': resumed and arm.read(0x05000002, 2) == 0x1567,
            'pass': first and repeat and stale_safe and irq_off and mixed
            and resumed and arm.read(0x05000002, 2) == 0x1567}


def invalidated_capture(path, intermediate, backdrop):
    arm = setup(path, 2, 0xC0)
    event(arm)
    mode(arm, intermediate)
    if backdrop:
        # Even an unchanged backdrop write observes the incompatible mode.
        arm.call('wsvVideoRegisterWriteCallback', 0x01)
    else:
        event(arm, 0x345)
    mode(arm, 0xC0)
    event(arm, 0x456)
    expected = legacy_palette(arm)
    complete(arm)
    first = publish(arm, expected)
    irq_off = not (arm.read(0x04000004, 2) & 0x20)
    arm.call('paletteRasterVCountIrq')
    stale_safe = bytes(arm.uc.mem_read(0x05000000, 256)) == expected
    return {'case': f'sticky-invalidation-{intermediate:02x}-'
            + ('backdrop' if backdrop else 'palette'),
            'legacy_preserved': first and stale_safe, 'irq_off': irq_off,
            'pass': first and stale_safe and irq_off}


def repeat_remap(path, events):
    arm = setup(path, 2, 0xC0)
    if events:
        event(arm)
    complete(arm)
    arm.call('paletteRasterVBlank')
    # A menu gamma/contrast change remaps the already completed raw colors.
    arm.write(arm.address('MAPPED_RGB') + 2, 0x3456, 2)
    arm.write(arm.address('MAPPED_RGB') + 0x234 * 2, 0x5678, 2)
    arm.write(0x05000002, 0x7777, 2)  # next host legacy DMA
    arm.call('paletteRasterVBlank')
    base = arm.read(0x05000002, 2)
    armed = bool(arm.read(0x04000004, 2) & 0x20)
    arm.call('paletteRasterVCountIrq')
    final = arm.read(0x05000002, 2)
    return {'case': f'repeated-remap-events-{events}', 'base': hex(base),
            'final': hex(final), 'irq': armed,
            'pass': base == 0x3456 and armed == bool(events)
            and final == (0x5678 if events else 0x3456)}


def actual_unpack_lifecycle(path):
    arm = setup(path, 2, 0xC0)
    arm.set('gGameHeader', arm.SCRATCH + 0x2000)
    event(arm)
    complete(arm)
    arm.call('paletteRasterVBlank')
    observations = []
    # Execute the actual unpackState wrapper and RAM copies; isolate the three
    # serialization engines. This checks lifecycle, not save-format correctness.
    def deserialize(uc, pc, size, data):
        observations.append(not arm.read(arm.address('wsvVideoWriteCallbackEnabled'), 1))
        mode(arm, 0)
        uc.reg_write(UC_ARM_REG_R0, 0)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
    for symbol in ('sphinxLoadState', 'V30LoadState', 'wsEepromLoadState'):
        entry = arm.address(symbol) & ~1
        arm.uc.hook_add(UC_HOOK_CODE, deserialize, begin=entry, end=entry)
    arm.uc.mem_write(arm.address('EMUPALBUFF'), b'\xAA\x55' * 512)
    arm.call('unpackState', arm.SCRATCH + 0x10000)
    rebuilt = bytes(arm.uc.mem_read(arm.address('EMUPALBUFF'), 256))
    expected = legacy_palette(arm)
    first = publish(arm, expected)
    arm.call('paletteRasterVCountIrq')
    no_stale = bytes(arm.uc.mem_read(0x05000000, 256)) == expected
    complete(arm)
    resumed = publish(arm, expected)
    return {'case': 'actual-unpack-palette-lifecycle', 'disabled_during_restore': observations,
            'legacy_rebuilt': rebuilt == expected,
            'pass': observations == [True] * 3 and rebuilt == expected
            and first and no_stale and resumed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('elf', type=Path)
    args = parser.parse_args()
    results = [mode_case(args.elf, soc, m) for soc in (0, 1, 2)
               for m in (0, 0x80, 0xC0, 0xE0)]
    results += [live_next_mode(args.elf)]
    results += [transitions(args.elf, m) for m in (0, 0x80)]
    results += [invalidated_capture(args.elf, m, backdrop)
                for m in (0, 0x80) for backdrop in (False, True)]
    results += [repeat_remap(args.elf, n) for n in (0, 1)]
    results.append(actual_unpack_lifecycle(args.elf))
    print(json.dumps({'evidence': 'linked ARM + synthetic MMIO; not game scanout',
                      'elf_sha256': hashlib.sha256(args.elf.read_bytes()).hexdigest(),
                      'results': results}, indent=2))
    return 0 if all(result['pass'] for result in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
