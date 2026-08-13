#!/usr/bin/env python3
"""Regression checks for monochrome WonderSwan internal RAM handling."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MEMORY = ROOT / "source" / "Memory.s"


class AswanRamSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MEMORY.read_text(encoding="utf-8")

    def test_byte_and_word_writes_have_mono_guards(self):
        self.assertIn("monoRamWriteGuardB", self.source)
        self.assertIn("monoRamWriteGuardW", self.source)
        self.assertRegex(
            self.source,
            re.compile(r"monoRamWriteGuardB:.*?cmp\s+r0,#0x10000000.*?bxcs\s+lr", re.S),
        )
        self.assertRegex(
            self.source,
            re.compile(r"monoRamWriteGuardW:.*?cmp\s+r0,#0x10000000.*?bxcs\s+lr", re.S),
        )

    def test_guards_are_runtime_selected(self):
        self.assertIn("setMonoRamMode", self.source)
        self.assertIn("monoRamModeB", self.source)
        self.assertIn("monoRamModeW", self.source)
        self.assertIn("cmp r0,#0x04000000", self.source)

    def test_unmapped_read_value_is_initialized(self):
        cart = (ROOT / "source" / "Cart.s").read_text(encoding="utf-8")
        self.assertRegex(cart, re.compile(r"wsRAM\+0x4000.*?mov(?:eq)?\s+r1,#0x90", re.S))


if __name__ == "__main__":
    unittest.main()
