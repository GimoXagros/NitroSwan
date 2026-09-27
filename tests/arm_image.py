#!/usr/bin/env python3
"""Execute linked ARM9 instructions with synthetic RAM and MMIO.

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
from unicorn.arm_const import UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7
from unicorn.arm_const import UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11


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
        self.write(self.address('sphinx0') + self.address('paletteRAM'), self.SCRATCH + 0x3000)

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

    def call(self, symbol, r0=0, r1=0, allowed_clobbers=()):
        preserved = (UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
                     UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11)
        for index, register in enumerate(preserved):
            self.uc.reg_write(register, 0xABC00000 + index)
        stack = self.uc.reg_read(UC_ARM_REG_SP)
        self.uc.reg_write(UC_ARM_REG_R0, r0)
        self.uc.reg_write(UC_ARM_REG_R1, r1)
        self.uc.reg_write(UC_ARM_REG_LR, self.RETURN)
        self.uc.emu_start(self.address(symbol), self.RETURN, count=2000000)
        if self.uc.reg_read(UC_ARM_REG_PC) != self.RETURN:
            raise AssertionError(f'{symbol}: instruction limit or unexpected stop')
        if self.uc.reg_read(UC_ARM_REG_SP) != stack:
            raise AssertionError(f'{symbol}: unbalanced stack')
        for index, register in enumerate(preserved):
            if register in allowed_clobbers:
                continue
            if self.uc.reg_read(register) != 0xABC00000 + index:
                raise AssertionError(f'{symbol}: clobbered callee-saved register {index + 4}')
        return self.uc.reg_read(UC_ARM_REG_R0)
