#!/usr/bin/env python3
"""Real linked ARM quiescence regression; synthetic MMIO, not DMA timing.

Arm the renderer through its real VBlank path, then check that a lifecycle
transition stops its repeated HBlank streams before any buffer reset. No ROM,
filesystem or DSpico driver is exercised by this test.
"""
import argparse
import hashlib
import json
from pathlib import Path

from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from validate_renderer_runtime import ArmImage


DMA0 = 0x040000B8
DMA3 = 0x040000DC
IME = 0x04000208
ENABLE = 1 << 31


def quiesce(path, entry, ime):
    arm = ArmImage(path)
    arm.stub('calculateFPS')
    arm.stub('scanKeys')
    arm.set('dmaScroll', arm.SCRATCH)
    arm.set('dmaWinInOut', arm.SCRATCH + 0x100)
    arm.set('dmaOamBuffer', arm.SCRATCH + 0x1000)
    arm.set('rendererQuiesced', 0, 1)
    arm.call('myVblank')
    armed = [arm.read(DMA0), arm.read(DMA3)]
    assert armed == [0x96600002, 0x96600003], armed
    # Unrelated DMA channels and IRQ clients are not owned by this transition.
    arm.write(0x040000C4, 0x12345678)
    arm.write(0x040000D0, 0x23456789)
    arm.write(IME, ime)
    arm.write(0x04000210, 0x00040005)  # FIFO, VCOUNT, VBLANK
    arm.write(0x04000004, 0x20, 2)
    reset_writes_safe = []
    first = arm.address('wsvObjTileSnapshots')
    last = first + 32768

    def reset_write(uc, access, address, size, value, data):
        if first <= address < last:
            reset_writes_safe.append(not ((arm.read(DMA0) | arm.read(DMA3)) & ENABLE))

    arm.uc.hook_add(UC_HOOK_MEM_WRITE, reset_write)
    arm.call(entry)
    stopped = [arm.read(DMA0), arm.read(DMA3)]
    ime_restored = arm.read(IME) == ime
    unrelated = arm.read(0x040000C4) == 0x12345678 and arm.read(0x040000D0) == 0x23456789
    irq_preserved = arm.read(0x04000210) & 0x40001 == 0x40001
    raster_stopped = entry != 'paletteRasterPrepareStateRestore' or not (
        arm.read(0x04000210) & 4 or arm.read(0x04000004, 2) & 0x20)
    scans = []
    scan = arm.address('scanKeys') & ~1
    arm.uc.hook_add(UC_HOOK_CODE, lambda *_: scans.append(1), begin=scan, end=scan)
    arm.call('myVblank')
    still_stopped = not ((arm.read(DMA0) | arm.read(DMA3)) & ENABLE)
    # A second quiesce is harmless; then a completed frame re-arms normally.
    arm.call(entry)
    arm.call('videoTileBufferFrameComplete', arm.SCRATCH + 0x1000)
    arm.call('videoTileBufferFrameCommit')
    arm.call('myVblank')
    resumed = [arm.read(DMA0), arm.read(DMA3)] == armed
    result = {
        'case': f'{entry}-ime-{ime}',
        'armed_controls': [hex(value) for value in armed],
        'controls_after_quiesce': [hex(value) for value in stopped],
        'reset_writes_after_stop': all(reset_writes_safe),
        'reset_observed': bool(reset_writes_safe),
        'input_scans': len(scans), 'ime_restored': ime_restored,
        'unrelated_dma_and_irq_preserved': unrelated and irq_preserved,
        'raster_stopped_when_requested': raster_stopped,
        'completed_frame_resumes_dma': resumed,
    }
    result['pass'] = (not ((stopped[0] | stopped[1]) & ENABLE)
                      and still_stopped and all(reset_writes_safe)
                      and bool(reset_writes_safe)
                      and len(scans) == 2 and ime_restored and unrelated
                      and irq_preserved and raster_stopped and resumed)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('elf', type=Path)
    args = parser.parse_args()
    results = [quiesce(args.elf, entry, ime)
               for entry in ('objTileBufferReset',
                             'paletteRasterPrepareStateRestore')
               for ime in (0, 1)]
    print(json.dumps({'evidence': 'linked ARM instructions, synthetic MMIO only',
                      'elf_sha256': hashlib.sha256(args.elf.read_bytes()).hexdigest(),
                      'results': results}, indent=2))
    return 0 if all(result['pass'] for result in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
