#!/usr/bin/env python3
"""Source-level contracts for cartridge ROM instruction-stream waitstates."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RomFetchWaitstateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.macros = (ROOT / "source" / "ARMV30MZ" / "ARMV30MZmac.h").read_text(
            encoding="utf-8"
        )
        cls.core = (ROOT / "source" / "ARMV30MZ" / "ARMV30MZ.s").read_text(
            encoding="utf-8"
        )
        cls.cpu = (ROOT / "source" / "cpu.s").read_text(encoding="utf-8")
        cls.video = (ROOT / "source" / "Sphinx" / "WSVideo.s").read_text(
            encoding="utf-8"
        )
        cls.memory = (ROOT / "source" / "Memory.s").read_text(encoding="utf-8")

    def test_hardware_wait_bit_is_bit_3(self):
        handler = re.search(r"^wsvHWW:.*?(?=^wsvTimerCtrlW:)", self.video, re.M | re.S)
        self.assertIsNotNone(handler)
        self.assertIn("tst r0,#0x08", handler.group(0))
        self.assertNotIn("tst r0,#0x04", handler.group(0))

    def test_waitstate_is_cached_at_a0_write(self):
        self.assertIn("FETCH_ROM_WAIT_FLAG", self.video)
        self.assertIn("FETCH_WAIT_ACTIVE_FLAG", self.video)
        self.assertNotIn("bl setRomWaitState", self.video)

    def test_all_instruction_stream_macros_apply_the_cached_delta(self):
        for macro in (
            "getNextByteTo",
            "getNextSignedByteTo",
            "getNextWordTo",
            "getNextSignedWordTo",
            "fetch",
            "executeNext",
        ):
            body = re.search(
                rf"^\s*\.macro {macro}\b.*?^\s*\.endm", self.macros, re.M | re.S
            )
            self.assertIsNotNone(body, macro)
            self.assertIn("eatFetchWait", body.group(0), macro)

    def test_cycle_delta_preserves_arm_condition_flags(self):
        helper = re.search(
            r"^\s*\.macro eatFetchWait\b.*?^\s*\.endm", self.macros, re.M | re.S
        )
        self.assertIsNotNone(helper)
        body = helper.group(0)
        self.assertIn("and \\scratch,v30cyc,#FETCH_WAIT_ACTIVE_FLAG", body)
        self.assertIn("sub v30cyc,v30cyc,\\scratch,lsl#3", body)
        self.assertNotIn("tst ", body)
        self.assertNotIn("subs ", body)

    def test_cached_cycle_delta_is_exactly_one_ws_cycle(self):
        cycle = 1 << 8
        active_flag = 1 << 5

        def apply(cycles, active):
            value = cycles | (active_flag if active else 0)
            scratch = value & active_flag
            return value - (scratch << 3)

        baseline = 20 * cycle
        self.assertEqual(apply(baseline, False) >> 8, 20)
        self.assertEqual(apply(baseline, True) >> 8, 19)

    def test_cached_toggle_preserves_region_state(self):
        cart_flag = 1 << 3
        wait_flag = 1 << 4
        active_flag = 1 << 5

        def write_a0(flags, value):
            flags &= ~(wait_flag | active_flag)
            if value & 0x08:
                flags |= wait_flag
                if flags & cart_flag:
                    flags |= active_flag
            return flags

        flags = cart_flag
        flags = write_a0(flags, 0x04)
        self.assertEqual(flags & active_flag, 0)
        flags = write_a0(flags, 0x0C)
        self.assertNotEqual(flags & active_flag, 0)
        flags = write_a0(flags, 0x04)
        self.assertEqual(flags & active_flag, 0)

    def test_physical_region_model_excludes_ram_sram_and_bios(self):
        def is_waited_rom(physical, mapped_to_bios):
            return physical >= 0x20000 and not mapped_to_bios

        self.assertFalse(is_waited_rom(0x0FFFF, False))
        self.assertFalse(is_waited_rom(0x10000, False))
        self.assertFalse(is_waited_rom(0x1FFFF, False))
        self.assertTrue(is_waited_rom(0x20000, False))
        self.assertTrue(is_waited_rom(0xFFFFF, False))
        self.assertFalse(is_waited_rom(0xFFFF0, True))

    def test_region_classifier_uses_physical_ws_address(self):
        classifier = re.search(
            r"^updateFetchRegion:.*?(?=^cpuReset:)", self.cpu, re.M | re.S
        )
        self.assertIsNotNone(classifier)
        body = classifier.group(0)
        self.assertIn("cmp r0,#0x20000000", body)
        self.assertIn("ldr r2,=biosBase", body)
        self.assertIn("cmp r3,#0x2000", body)
        self.assertIn("FETCH_CART_ROM_FLAG", body)

    def test_pc_encode_calls_classifier_without_touching_data_reads(self):
        self.assertEqual(self.core.count("blx r2"), 2)
        self.assertIn("v30FetchRegionFunc", self.core)
        self.assertNotIn("FETCH_WAIT", self.memory)
        self.assertNotIn("v30FetchRegionFunc", self.memory)

    def test_dspico_cache_path_is_not_coupled_to_timing(self):
        cache = (ROOT / "source" / "DspicoRomCache.c").read_text(encoding="utf-8")
        self.assertNotIn("FETCH_WAIT", cache)
        self.assertNotIn("wsvSystemCtrl1", cache)


if __name__ == "__main__":
    unittest.main()
