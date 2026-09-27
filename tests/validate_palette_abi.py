#!/usr/bin/env python3
"""Execute the affected host ARM bridges; synthetic RAM/MMIO, not whole CPU proof."""
import argparse
import hashlib
import json
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from validate_palette_runtime import setup


def watch_entry(arm, symbol):
    observed = []
    entry = arm.address(symbol) & ~1
    def watch(uc, pc, size, data):
        observed.append(uc.reg_read(UC_ARM_REG_SP) & 7)
    arm.uc.hook_add(UC_HOOK_CODE, watch, begin=entry, end=entry)
    return observed


def register_bridge(path, entry, stack_mod, port=1):
    arm = setup(path, 2, 0xC0)
    arm.uc.reg_write(UC_ARM_REG_SP, 0x02EFFF00 - stack_mod)
    # Install only the two real Sphinx dispatch entries exercised here.
    arm.write(arm.address('ioOutTable') + 4, arm.address('wsvBgColorW'))
    arm.write(arm.address('ioOutTable') + 8, arm.address('wsvReadOnlyW'))
    target = ('paletteRasterCaptureRegisterWrite' if 'paletteRasterCaptureRegisterWrite'
              in arm.symbols else 'wsvVideoRegisterWriteCallback')
    observed = watch_entry(arm, target)
    # Odd word I/O intentionally charges v30cyc/r10; it is an internal guest ABI.
    arm.call(entry, 1, port, allowed_clobbers=(UC_ARM_REG_R10,) if entry == 'v30WritePort16' else ())
    return {'case': f'{entry}-sp{stack_mod}', 'c_entry_sp_mod8': observed,
            'pass': observed == [0]}


def memory_bridge(path, word, stack_mod):
    arm = setup(path, 2, 0xC0)
    observed = watch_entry(arm, 'paletteRasterCapturePaletteWrite')
    address = 0xFE03 if word else 0xFE02
    ptr = arm.address('V30OpTable')
    ram = arm.address('wsRAM')
    arm.write(ptr + arm.address('v30MemTblInv') - 4, ram)
    arm.uc.reg_write(UC_ARM_REG_R11, ptr)
    arm.uc.reg_write(UC_ARM_REG_R4, 0xABCD1234)
    arm.uc.reg_write(UC_ARM_REG_SP, 0x02EFFF00 - stack_mod)
    arm.uc.reg_write(UC_ARM_REG_R0, address << 12)
    arm.uc.reg_write(UC_ARM_REG_R1, 0x1234)
    arm.uc.reg_write(UC_ARM_REG_LR, arm.RETURN)
    stack = arm.uc.reg_read(UC_ARM_REG_SP)
    symbol = 'cpuWriteMem20W' if word else 'cpuWriteMem20'
    arm.uc.emu_start(arm.address(symbol), arm.RETURN, count=2000000)
    balanced = arm.uc.reg_read(UC_ARM_REG_SP) == stack
    stored = bytes(arm.uc.mem_read(ram + address, 2 if word else 1))
    operands = (arm.uc.reg_read(UC_ARM_REG_R0), arm.uc.reg_read(UC_ARM_REG_R1))
    return {'case': f'{symbol}-sp{stack_mod}', 'c_entry_sp_mod8': observed, 'stored': stored.hex(),
            'pass': observed == [0] * (2 if word else 1) and balanced
            and arm.uc.reg_read(UC_ARM_REG_PC) == arm.RETURN
            and arm.uc.reg_read(UC_ARM_REG_R4) == 0xABCD1234
            and operands == (((address + 1) << 12, 0x12) if word else (address << 12, 0x1234))
            and stored == (b'\x34\x12' if word else b'\x34')}


def dma_bridge(path, word):
    arm = setup(path, 2, 0xC0)
    ptr, ram, sphinx = (arm.address(name) for name in ('V30OpTable', 'wsRAM', 'sphinx0'))
    arm.write(ptr + arm.address('v30MemTblInv') - 4, ram)
    arm.write(arm.address('ioOutTable') + 0x48 * 4, arm.address('wsvDMACtrlW'))
    arm.write(arm.address('ioOutTable') + 0x49 * 4, arm.address('wsvReadOnlyW'))
    arm.write(sphinx + arm.address('wsvDMASource'), 0x2000)
    arm.write(sphinx + arm.address('wsvDMADest'), (2 << 16) | 0xFE02)
    arm.write(sphinx + arm.address('paletteRAM'), ram + 0xFE00)
    arm.write(ram + 0x2000, 0x1234, 2)
    arm.uc.reg_write(UC_ARM_REG_R11, ptr)
    arm.uc.reg_write(UC_ARM_REG_R0, 0x80)
    arm.uc.reg_write(UC_ARM_REG_R1, 0x48)
    arm.uc.reg_write(UC_ARM_REG_LR, arm.RETURN)
    observed = watch_entry(arm, 'paletteRasterCapturePaletteWrite')
    stack = arm.uc.reg_read(UC_ARM_REG_SP)
    symbol = 'v30WritePort16' if word else 'v30WritePort'
    arm.uc.emu_start(arm.address(symbol), arm.RETURN, count=2000000)
    return {'case': f'{symbol}-DMA48-palette', 'c_entry_sp_mod8': observed,
            'pass': observed == [0] and arm.read(ram + 0xFE02, 2) == 0x1234
            and arm.uc.reg_read(UC_ARM_REG_PC) == arm.RETURN
            and arm.uc.reg_read(UC_ARM_REG_SP) == stack}


def frame_bridge(path, direct):
    arm = setup(path, 2, 0xC0)
    # Real frame bridge + real palette completion, isolated from tile/OAM work.
    for symbol in ('wsvCopyScrollValues', 'copyWindowValues', 'wsvConvertSprites',
                   'paletteTxAll', 'updateSlowIO'):
        arm.stub(symbol)
    observed = watch_entry(arm, 'paletteRasterFrameComplete')
    arm.uc.reg_write(UC_ARM_REG_R12, arm.address('sphinx0'))
    # Normal run->scanline->endFrame arrives 4 mod 8; direct C refresh arrives 0.
    arm.uc.reg_write(UC_ARM_REG_SP, 0x02EFFF00 - (0 if direct else 4))
    entry = 'gfxRefresh' if direct else 'gfxEndFrame'
    arm.call(entry)
    return {'case': entry, 'c_entry_sp_mod8': observed, 'pass': observed == [0]}


def step_scanline_bridge(path):
    arm = setup(path, 2, 0xC0)
    arm.call('cpuInit')
    ptr, ram = arm.address('V30OpTable'), arm.address('wsRAM')
    arm.write(ptr + arm.address('v30MemTblInv') - 4, ram)
    # Real V30 instructions: MOV AL,34h; MOV [FE02h],AL; HLT.
    arm.uc.mem_write(ram + 0x1000, bytes.fromhex('B0 34 A2 02 FE F4'))
    # These CPU-state symbols are negative offsets represented as unsigned ELF values.
    arm.write((ptr + arm.address('v30PC')) & 0xFFFFFFFF, ram + 0x1000)
    arm.write((ptr + arm.address('v30LastBank')) & 0xFFFFFFFF, ram)
    arm.write(arm.address('sphinx0') + arm.address('paletteRAM'), ram + 0xFE00)
    # Only skip post-CPU scanline rendering; execute the actual stepping/CPU stack.
    arm.stub('wsvDoScanline')
    observed = watch_entry(arm, 'paletteRasterCapturePaletteWrite')
    arm.call('stepScanLine')
    return {'case': 'stepScanLine-guest-palette-write', 'c_entry_sp_mod8': observed,
            'pass': observed == [0] and arm.read(ram + 0xFE02, 1) == 0x34}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('elf', type=Path)
    args = parser.parse_args()
    results = [register_bridge(args.elf, 'wsvVideoRegisterWriteCallback', n) for n in (0, 4)]
    results += [register_bridge(args.elf, entry, 0) for entry in ('v30WritePort', 'v30WritePort16')]
    results += [memory_bridge(args.elf, word, mod) for word in (False, True) for mod in (0, 4)]
    results += [dma_bridge(args.elf, word) for word in (False, True)]
    results += [frame_bridge(args.elf, direct) for direct in (False, True)]
    results.append(step_scanline_bridge(args.elf))
    print(json.dumps({'evidence': 'linked ARM bridges, synthetic caller state; not full host ABI',
                      'elf_sha256': hashlib.sha256(args.elf.read_bytes()).hexdigest(),
                      'results': results}, indent=2))
    return 0 if all(row['pass'] for row in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
