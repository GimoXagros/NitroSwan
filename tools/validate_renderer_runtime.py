#!/usr/bin/env python3
"""Execute linked ARM9 renderer instructions with synthetic RAM and MMIO.

Requires unicorn and pyelftools. This is an instruction-level regression, not
a DS emulator, DMA timing test, game scene comparison or hardware validation.
"""

import argparse
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_PC, UC_ARM_REG_SP, UC_ARM_REG_LR


class ArmImage:
    RETURN = 0x02F00000
    SCRATCH = 0x02E00000

    def __init__(self, path):
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.symbols = {}
        for start, size in ((0x01000000, 0x10000), (0x02000000, 0x1000000),
                            (0x04000000, 0x10000), (0x05000000, 0x10000),
                            (0x06000000, 0x800000), (0x07000000, 0x10000)):
            self.uc.mem_map(start, size)
        with path.open('rb') as source:
            elf = ELFFile(source)
            for section in elf.iter_sections():
                if section['sh_flags'] & 2 and section['sh_size'] and section['sh_type'] != 'SHT_NOBITS':
                    self.uc.mem_write(section['sh_addr'], section.data())
            for symbol in elf.get_section_by_name('.symtab').iter_symbols():
                if symbol.name and symbol['st_shndx'] != 'SHN_UNDEF':
                    self.symbols.setdefault(symbol.name, []).append(symbol['st_value'])
        self.uc.reg_write(UC_ARM_REG_SP, 0x02EFFF00)

    def address(self, symbol):
        values = set(self.symbols[symbol])
        if len(values) != 1:
            raise AssertionError(f'ambiguous ELF symbol: {symbol}')
        return values.pop()

    def write(self, address, value, size=4):
        self.uc.mem_write(address, value.to_bytes(size, 'little', signed=value < 0))

    def read(self, address, size=4):
        return int.from_bytes(self.uc.mem_read(address, size), 'little')

    def set(self, symbol, value, size=4):
        self.write(self.address(symbol), value, size)

    def stub(self, symbol):
        address = self.address(symbol) & ~1
        def skip(uc, pc, size, data):
            if pc == address:
                uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        self.uc.hook_add(UC_HOOK_CODE, skip, begin=address, end=address)

    def call(self, symbol, r0=0, r1=0):
        self.uc.reg_write(UC_ARM_REG_R0, r0)
        self.uc.reg_write(UC_ARM_REG_R1, r1)
        self.uc.reg_write(UC_ARM_REG_LR, self.RETURN)
        self.uc.emu_start(self.address(symbol), self.RETURN, count=2000000)
        if self.uc.reg_read(UC_ARM_REG_PC) != self.RETURN:
            raise AssertionError(f'{symbol}: instruction limit or unexpected stop')
        return self.uc.reg_read(UC_ARM_REG_R0)


def oam_source(path, scroll, completed):
    arm = ArmImage(path)
    arm.stub('calculateFPS')
    arm.stub('scanKeys')
    arm.set('dmaScroll', arm.SCRATCH)
    arm.write(arm.SCRATCH + 4, scroll)
    arm.set('dmaWinInOut', arm.SCRATCH + 0x100)
    fallback = arm.SCRATCH + 0x2000
    arm.set('dmaOamBuffer', fallback)
    transfers = []
    def dma(uc, access, address, size, value, data):
        if address == 0x040000DC and value == 0x84000100:
            if arm.read(0x040000D8) == 0x07000000:
                transfers.append(arm.read(0x040000D4))
    arm.uc.hook_add(UC_HOOK_MEM_WRITE, dma)
    arm.call('vblIrqHandler', completed)
    expected = completed or fallback
    return {'case': f'oam-scroll-{scroll:08x}-completed-{bool(completed)}',
            'expected_source': expected, 'actual_sources': transfers,
            'pass': transfers == [expected]}


def palette_repeat(path, events):
    arm = ArmImage(path)
    arm.set('rasterEnabled', 1, 1)
    arm.set('readyFrame', 0)
    arm.set('activeFrame', -1)
    frame = arm.address('frames')
    # base[128], delta[384] {u8 line,index; u16 color}, count, dropped.
    arm.write(frame + 2, 0x1234, 2)
    arm.uc.mem_write(frame + 256, struct.pack('<BBH', 5, 1, 0x4321))
    arm.write(frame + 256 + 384 * 4, events, 2)
    arm.call('paletteRasterVBlank')
    arm.write(0x05000002, 0x9999, 2)  # next host palette DMA, no new WS frame
    arm.call('paletteRasterVBlank')
    base = arm.read(0x05000002, 2)
    enabled = bool(arm.read(0x04000004, 2) & 0x20)
    return {'case': f'palette-repeat-events-{events}', 'base': base,
            'vcount_enabled': enabled,
            'pass': base == 0x1234 and enabled == bool(events)}


def palette_ownership(path):
    arm = ArmImage(path)
    arm.call('objTileBufferReset')
    arm.call('objTileBufferCompleteStateRestore', 0xC0)
    palette = arm.address('EMUPALBUFF') + 512
    arm.uc.mem_write(palette, b'\x34\x12' * 256)
    arm.call('videoTileBufferFrameComplete', arm.SCRATCH)
    arm.call('videoTileBufferFrameCommit')
    arm.uc.mem_write(palette, b'\x78\x56' * 256)  # next WS frame in progress
    arm.call('videoTileBufferVBlank')
    live = bytes(arm.uc.mem_read(palette, 512))
    if 'videoTileBufferPublishPalette' in arm.symbols:
        arm.call('videoTileBufferPublishPalette')
        published = bytes(arm.uc.mem_read(0x05000200, 512))
    else:
        published = live  # r8 subsequently DMA-copies this live buffer
    return {'case': 'vblank-does-not-write-live-obj-palette',
            'live_preserved': live == b'\x78\x56' * 256,
            'completed_palette_published': published == b'\x34\x12' * 256,
            'pass': live == b'\x78\x56' * 256 and published == b'\x34\x12' * 256}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('elf', type=Path)
    args = parser.parse_args()
    results = [oam_source(args.elf, scroll, completed)
               for scroll in (0, 0x00010002, 0x00FF00FF)
               for completed in (0, ArmImage.SCRATCH + 0x1000)]
    results += [palette_repeat(args.elf, events) for events in (0, 1)]
    results.append(palette_ownership(args.elf))
    print(json.dumps({'evidence': 'linked ARM instructions, synthetic MMIO',
                      'results': results}, indent=2))
    return 0 if all(result['pass'] for result in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
