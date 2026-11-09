#!/usr/bin/env python3
"""Execute linked RTC command/data routines with synthetic chip state.

Seconds and AM/PM vectors include asie/ws-rtc-test 071687a; calendar expectations
use Python's Gregorian calendar for 2000..2099. This is not cartridge, alarm/IRQ,
bus timing or full test-ROM validation. Requires existing unicorn/pyelftools.
"""
import argparse
import calendar
import hashlib
import json
from pathlib import Path

from validate_renderer_runtime import ArmImage


def expect(actual, expected, label):
    if actual != expected:
        raise AssertionError(f'{label}: expected {expected!r}, got {actual!r}')


def bcd(value):
    return (value // 10) * 16 + value % 10


class Rtc:
    def __init__(self, arm):
        self.arm = arm
        self.chip = arm.SCRATCH + 0x5000
        for symbol, offset in {'wsRtcSize': 20, 'wsRtcState': 4,
                               'wsRtcStateEnd': 20, 'rtcYear': 8,
                               'rtcHour': 12, 'rtcSecond': 14}.items():
            expect(arm.address(symbol), offset, symbol)
        arm.uc.mem_write(self.chip - 4, b'\xA5' * 28)
        self.call('wsRtcReset')
        expect(self.call('wsRtcStatusR'), 0, 'first status read after reset')
        expect(self.call('wsRtcStatusR'), 0x80, 'second status read after reset')
        expect(bytes(arm.uc.mem_read(self.chip + 8, 7)),
               bytes((0, 1, 1, 0, 0, 0, 0)), 'reset calendar')
        expect(arm.call('wsRtcGetStateSize'), 16, 'serialized state size')
        self.write(0x12, (0x40,))

    def call(self, name, value=0):
        result = self.arm.call(name, self.chip, value)
        expect(bytes(self.arm.uc.mem_read(self.chip - 4, 4)), b'\xA5' * 4,
               f'{name} leading guard')
        expect(bytes(self.arm.uc.mem_read(self.chip + 20, 4)), b'\xA5' * 4,
               f'{name} trailing guard')
        return result

    def ready(self):
        self.call('wsRtcStatusR')
        expect(self.call('wsRtcStatusR') & 0x80, 0x80, 'status-read ready handshake')

    def write(self, command, values):
        self.call('wsRtcCommandW', command)
        self.ready()
        for value in values:
            self.call('wsRtcDataW', value)
            self.ready()

    def read(self, command=0x15, length=7):
        self.call('wsRtcCommandW', command)
        self.ready()
        values = []
        for _ in range(length):
            values.append(self.call('wsRtcDataR'))
            self.ready()
        return values

    def tick(self):
        # r1 is not an argument in this fork; WSCart already owns the cycle timer.
        self.call('wsRtcUpdate', 0xDEADBEEF)


def seconds(path):
    rtc = Rtc(ArmImage(path))
    for value in range(256):
        rtc.write(0x16, (0, 0, value))
        masked = value & 0x7F
        expect(rtc.read(0x17, 3), [0, 0, masked], f'seconds immediate {value:02x}')
        rtc.tick()
        decimal = (masked >> 4) * 10 + (masked & 15)
        valid = (masked & 15) < 10 and decimal < 60
        expected = [0, 0, bcd(decimal + 1)] if valid and decimal < 59 else [0, 1, 0]
        expect(rtc.read(0x17, 3), expected, f'seconds tick {value:02x}')
    return {'case': 'seconds-mask-deferred-correction-and-carry', 'vectors': 256, 'pass': True}


def calendar_boundaries(path):
    rtc = Rtc(ArmImage(path))
    for year in range(100):
        rtc.write(0x14, (bcd(year), 2, 0x29, 0, 0, 0, 0))
        date = [bcd(year), 2, 0x29] if calendar.isleap(2000 + year) else [bcd(year), 3, 1]
        expect(rtc.read()[:3], date, f'February 29 write {year:02d}')
        for month in range(1, 13):
            last = calendar.monthrange(2000 + year, month)[1]
            rtc.write(0x14, (bcd(year), bcd(month), bcd(last), 6, 0x23, 0x59, 0x59))
            rtc.tick()
            next_year = (year + 1) % 100 if month == 12 else year
            next_month = 1 if month == 12 else month + 1
            expect(rtc.read(), [bcd(next_year), bcd(next_month), 1, 0, 0, 0, 0],
                   f'month-end {year:02d}-{month:02d}')
    return {'case': 'all-years-February-writes-and-month-end-ticks', 'vectors': 1300, 'pass': True}


def isolated_writes(path):
    rtc = Rtc(ArmImage(path))
    rtc.write(0x14, (0x23, 1, 0x31, 0, 0, 0, 0))
    rtc.write(0x14, (0x23, 2))
    rtc.write(0x16, (0, 0x6A, 0xE5))
    expect(rtc.read(), [0x23, 2, 0x31, 0, 0, 0, 0x65],
           'TIME write must not normalize unrelated date fields')
    rtc.write(0x14, (0x23, 2, 0x31, 0, 0, 0, 0))
    expect(rtc.read(), [0x23, 3, 1, 0, 0, 0, 0], 'explicit day write rolls over')
    rtc.write(0x14, (0xFA, 0x13, 0, 7, 0x27, 0x6A, 0xE5))
    expect(rtc.read(), [0, 1, 1, 0, 0, 0, 0x65], 'invalid individual fields')
    return {'case': 'per-register-write-correction', 'vectors': 3, 'pass': True}


def hour_modes(path):
    rtc = Rtc(ArmImage(path))
    for hour in range(24):
        pm = 0x80 if hour >= 12 else 0
        rtc.write(0x12, (0x40,))
        rtc.write(0x16, (bcd(hour), 0, 0))
        expect(rtc.read(0x17, 3), [bcd(hour) | pm, 0, 0], f'24h read {hour}')
        rtc.write(0x12, (0,))
        expect(rtc.read(0x17, 3), [bcd(hour % 12) | pm, 0, 0], f'24h to 12h {hour}')
        rtc.write(0x16, (bcd(hour % 12) | pm, 0, 0))
        rtc.write(0x12, (0x40,))
        expect(rtc.read(0x17, 3), [bcd(hour) | pm, 0, 0], f'12h to 24h {hour}')
    for invalid in (0x8A, 0x92, 0xFF):
        rtc.write(0x12, (0,))
        rtc.write(0x16, (invalid, 0, 0))
        expect(rtc.read(0x17, 3), [0, 0, 0], f'invalid 12h read {invalid:02x}')
        rtc.write(0x12, (0x40,))
        expect(rtc.read(0x17, 3), [0, 0, 0], f'invalid 12h to 24h {invalid:02x}')
    return {'case': 'all-valid-hour-conversions-and-invalid-12h-guards',
            'vectors': 78, 'pass': True}


def save_state(path):
    arm = ArmImage(path)
    rtc = Rtc(arm)
    rtc.write(0x14, (0x24, 2, 0x29, 4, 0x13, 0x45, 0xE5))
    saved = bytes(arm.uc.mem_read(rtc.chip + 4, 16))
    callback = arm.read(rtc.chip)
    buffer = arm.SCRATCH + 0x6000
    arm.uc.mem_write(buffer - 4, b'\xA5' * 24)
    expect(arm.call('wsRtcSaveState', buffer, rtc.chip), 16, 'save return size')
    expect(bytes(arm.uc.mem_read(buffer, 16)), saved, 'save bytes')
    expect(bytes(arm.uc.mem_read(buffer - 4, 4)), b'\xA5' * 4, 'save leading guard')
    expect(bytes(arm.uc.mem_read(buffer + 16, 4)), b'\xA5' * 4, 'save trailing guard')
    arm.uc.mem_write(rtc.chip + 4, b'\x55' * 16)
    expect(rtc.call('wsRtcLoadState', buffer), 16, 'load return size')
    expect(bytes(arm.uc.mem_read(rtc.chip + 4, 16)), saved, 'load bytes')
    expect(arm.read(rtc.chip), callback, 'load preserves interrupt callback')
    expect(rtc.read(), [0x24, 2, 0x29, 4, 0x93, 0x45, 0x65], 'read after load')
    rtc.tick()
    expect(rtc.read(), [0x24, 2, 0x29, 4, 0x93, 0x46, 0], 'one-second tick after load')
    return {'case': '20-byte-chip-16-byte-save-and-one-second-ABI', 'pass': True}


def negative_control(path, saturation):
    arm = ArmImage(path)
    if saturation:
        address = arm.address('fixupSecond')
        expect(arm.read(address), 0xE201107F, 'negative-control seconds mask instruction')
        arm.write(address, 0xE3A01059)  # mov r1,#0x59: withdrawn eager saturation.
    else:
        address = arm.address('invalidSecond') + 8
        instruction = arm.read(address)
        expect(instruction >> 24, 0x4A, 'negative-control BMI instruction')
        arm.write(address, instruction | 0xE0000000)  # Always skip minute carry.
    rtc = Rtc(arm)
    rtc.write(0x16, (0, 0, 0xE5))
    immediate = rtc.read(0x17, 3)
    rtc.tick()
    delayed = rtc.read(0x17, 3)
    detected = immediate != [0, 0, 0x65] or delayed != [0, 1, 0]
    return {'case': 'negative-eager-saturation' if saturation else 'negative-no-carry',
            'immediate': immediate, 'after_tick': delayed, 'pass': detected}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('elf', type=Path)
    args = parser.parse_args()
    results = []
    for test in (seconds, calendar_boundaries, isolated_writes, hour_modes, save_state):
        try:
            results.append(test(args.elf))
        except AssertionError as error:
            results.append({'case': test.__name__, 'pass': False, 'error': str(error)})
    for saturation in (False, True):
        results.append(negative_control(args.elf, saturation))
    print(json.dumps({'evidence': 'linked ARM instructions; synthetic RTC state; no hardware/IRQ claim',
                      'elf_sha256': hashlib.sha256(args.elf.read_bytes()).hexdigest(),
                      'results': results}, indent=2))
    return 0 if all(result['pass'] for result in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
