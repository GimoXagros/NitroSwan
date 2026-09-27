#!/usr/bin/env python3
"""Linked ARM 2bpp bank/address tests with an independent pixel decode oracle.

Synthetic guest tiles only: no game assets, DS scanout or DMA timing emulation.
"""
import argparse
import hashlib
import json
from pathlib import Path

from unicorn.arm_const import UC_ARM_REG_R12
from validate_renderer_runtime import ArmImage

BG = 0x06008000
OBJ = 0x06400000
REGION_SIZE = 0x10000


def setup(path, mode):
    arm = ArmImage(path)
    arm.uc.reg_write(UC_ARM_REG_R12, arm.address('sphinx0'))
    arm.call('wsVideoInit', arm.address('wsRAM'))
    arm.write(arm.address('sphinx0') + arm.address('wsvVideoMode'), mode, 1)
    arm.uc.mem_write(BG, b'\xA5' * REGION_SIZE)
    arm.uc.mem_write(OBJ, b'\x5A' * REGION_SIZE)
    return arm


def pixels(source, opaque):
    result = bytearray()
    for row in range(0, len(source), 2):
        low, high = source[row:row + 2]
        word = 0
        for x in range(8):
            value = ((low >> (7 - x)) & 1) | (((high >> (7 - x)) & 1) << 1)
            word |= (value | (4 if opaque else 0)) << (4 * x)
        result.extend(word.to_bytes(4, 'little'))
    return result


def apply_expected(bg, obj, offset, source, groups):
    for group in groups:
        raw = source[group * 32:(group + 1) * 32]
        for half, opaque in ((0, True), (0x4000, False)):
            decoded = pixels(raw, opaque)
            start = offset + half + group * 64
            bg[start:start + 64] = decoded
            start = half + group * 64
            obj[start:start + 64] = decoded


def compare(arm, bg, obj):
    errors = {}
    for name, address, expected in (('bg', BG, bg), ('obj', OBJ, obj)):
        actual = arm.uc.mem_read(address, REGION_SIZE)
        mismatch = [i for i, (a, e) in enumerate(zip(actual, expected)) if a != e]
        errors[name] = {'wrong_bytes': len(mismatch),
                        'first_addresses': [hex(address + i) for i in mismatch[:4]]}
    return errors


def conversion(path, mode, offset, sparse):
    arm = setup(path, mode)
    source = bytes(((i * 29) ^ (i >> 3) ^ 0x96) & 255 for i in range(0x2000))
    groups = (0, 127, 255) if sparse else range(256)
    dirty = bytearray(b'\x44' * 256)
    for group in groups:
        dirty[group] = 0
    arm.uc.mem_write(arm.address('wsRAM') + 0x2000, source)
    arm.uc.mem_write(arm.address('DIRTYTILES') + 0x100, bytes(dirty))
    arm.set('wsvBgTileOffset', offset, 2)
    arm.set('wsvObjTileOffset', 512, 2)  # 2bpp still uses fixed OBJ destinations.
    bg = bytearray(b'\xA5' * REGION_SIZE)
    obj = bytearray(b'\x5A' * REGION_SIZE)
    apply_expected(bg, obj, offset, source, groups)
    arm.call('transferVRAM4Planar')
    errors = compare(arm, bg, obj)
    clean = bytes(arm.uc.mem_read(arm.address('DIRTYTILES') + 0x100, 256)) == b'\x44' * 256
    return {'case': f'2bpp-mode-{mode:02x}-bank-{offset:04x}-sparse-{sparse}',
            'regions': errors, 'dirty_consumed': clean,
            'pass': clean and all(e['wrong_bytes'] == 0 for e in errors.values())}


def lifecycle(path, mode):
    arm = setup(path, mode)
    arm.call('objTileBufferReset')
    bg = bytearray(b'\xA5' * REGION_SIZE)
    obj = bytearray(b'\x5A' * REGION_SIZE)
    previous_offset = 0
    frames = []
    for index, groups in enumerate((range(256), (0, 127, 255), (), (1, 128, 254))):
        source = bytes(((i * 31) ^ (i >> 4) ^ (index * 73)) & 255 for i in range(0x2000))
        dirty = bytearray(b'\x44' * 256)
        for group in groups:
            dirty[group] = 0
        arm.uc.mem_write(arm.address('wsRAM') + 0x2000, source)
        arm.uc.mem_write(arm.address('DIRTYTILES') + 0x100, bytes(dirty))
        offset = previous_offset ^ 0x8000 if groups else previous_offset
        if groups:
            bg[offset:offset + 0x8000] = bg[previous_offset:previous_offset + 0x8000]
        apply_expected(bg, obj, offset, source, groups)
        arm.call('objTileBufferBeginFrame', mode)
        arm.call('transferVRAM4Planar')
        arm.call('videoTileBufferFrameComplete', arm.SCRATCH)
        arm.call('videoTileBufferFrameCommit')
        arm.call('videoTileBufferVBlank')
        arm.call('videoTileBufferVBlank')  # repeated refresh without guest work
        errors = compare(arm, bg, obj)
        selected = (arm.read(0x04000008, 2) >> 2) & 15
        frames.append({'frame': index, 'regions': errors, 'selected_char_base': selected,
                       'pass': selected == 2 + (offset >> 14)
                       and all(e['wrong_bytes'] == 0 for e in errors.values())})
        previous_offset = offset
    return {'case': f'2bpp-dirty-clean-publication-{mode:02x}', 'frames': frames,
            'pass': all(frame['pass'] for frame in frames)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('elf', type=Path)
    args = parser.parse_args()
    results = [conversion(args.elf, mode, offset, sparse)
               for mode in (0, 0x80) for offset in (0, 0x8000) for sparse in (False, True)]
    results += [lifecycle(args.elf, mode) for mode in (0, 0x80)]
    print(json.dumps({'evidence': 'linked ARM, synthetic planar tiles and MMIO',
                      'elf_sha256': hashlib.sha256(args.elf.read_bytes()).hexdigest(),
                      'results': results}, indent=2))
    return 0 if all(result['pass'] for result in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
