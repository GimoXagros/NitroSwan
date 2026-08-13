#!/usr/bin/env python3
"""Regression checks for opt-in idle-loop hacks and hot-path rejection."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SpeedCoreTests(unittest.TestCase):
    def test_speed_hacks_only_initialize_from_established_menu_path(self):
        cart = (ROOT / "source/Cart.s").read_text(encoding="utf-8")
        block = cart[cart.index("loadCart:"):cart.index("clearDirtyTiles:")]
        self.assertIn("bl cpuReset", block)
        self.assertNotIn("bl hacksInit", block)

        gui = (ROOT / "source/Gui.c").read_text(encoding="utf-8")
        toggle = gui[gui.index("void speedHackSet()"):gui.index("const char *getSpeedHackText()")]
        self.assertIn("hacksInit();", toggle)

    def test_self_modifying_handlers_are_cache_coherent(self):
        hacks = (ROOT / "source/SpeedHacks.s").read_text(encoding="utf-8")
        cache = (ROOT / "source/SpeedHacksCache.c").read_text(encoding="utf-8")
        self.assertIn("bl speedHacksSync", hacks)
        self.assertIn("sngJR_hackEnd:", hacks)
        self.assertIn("DC_FlushRange", cache)
        self.assertIn("IC_InvalidateRange", cache)

    def test_hacks_remain_user_controlled_and_game_bounded(self):
        hacks = (ROOT / "source/SpeedHacks.s").read_text(encoding="utf-8")
        self.assertIn("tst r0,#0x20000", hacks)
        self.assertIn("cmp r0,#0x1B", hacks)
        self.assertIn("beq noHacks", hacks)

    def test_release_has_no_diagnostic_autoload(self):
        main = (ROOT / "source/Main.c").read_text(encoding="utf-8")
        self.assertNotIn("defaultExceptionHandler", main)
        self.assertNotIn("/ws/test_ascii.wsc", main)


if __name__ == "__main__":
    unittest.main()
