#!/usr/bin/env python3
"""Source-level checks that unstable hot-path timing changes stay excluded."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TimingCoreTests(unittest.TestCase):
    def test_rep_handlers_use_the_custom_baseline_loops(self):
        source = (ROOT / "source" / "ARMV30MZ" / "ARMV30MZ.s").read_text(encoding="utf-8")
        variants = re.findall(r"^f[23](?:6[c-f]|a[4-7a-f]):", source, re.M)
        self.assertEqual(len(variants), 18)
        self.assertNotIn("CheckRepInterrupt", source)
        self.assertNotIn("breakRepCommon:", source)

    def test_unverified_rom_waitstate_is_not_in_memory_hot_paths(self):
        memory = (ROOT / "source" / "Memory.s").read_text(encoding="utf-8")
        video = (ROOT / "source" / "Sphinx" / "WSVideo.s").read_text(encoding="utf-8")
        self.assertNotIn("setRomWaitState", memory)
        self.assertNotIn("romWaitStateB:", memory)
        self.assertNotIn("romWaitStateW:", memory)
        self.assertNotIn("bl setRomWaitState", video)


if __name__ == "__main__":
    unittest.main()
