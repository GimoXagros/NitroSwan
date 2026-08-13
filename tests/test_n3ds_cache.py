#!/usr/bin/env python3
"""Static regression checks for the New 3DS extended-RAM MPU mapping."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class N3dsCacheTests(unittest.TestCase):
    def test_mpu_transition_keeps_main_ram_mapped(self):
        source = (ROOT / "source" / "Shared" / "AsmExtra.s").read_text(encoding="utf-8")
        enable = source.index("enableN3dsExtraCache:")
        main = source.index("0x0200002F", enable)
        extra = source.index("0x0C000031", enable)
        self.assertLess(main, extra)
        self.assertIn("mcr p15,0,r0,c7,c14,0", source[enable:extra])

    def test_restore_and_type_dispatch_are_present(self):
        asm = (ROOT / "source" / "Shared" / "AsmExtra.s").read_text(encoding="utf-8")
        cart = (ROOT / "source" / "Shared" / "CartridgeRAM.c").read_text(encoding="utf-8")
        files = (ROOT / "source" / "FileHandling.c").read_text(encoding="utf-8")
        self.assertIn("disableN3dsExtraCache:", asm)
        self.assertIn("0x0300002D", asm)
        self.assertIn("rType == N3DS_RAM", cart)
        unlock = cart[cart.index("vu16 *cartRamUnlock"):cart.index("void cartRamLock")]
        self.assertIn("disableN3dsExtraCache", unlock)
        self.assertIn("cartRamEnableCache();", files)


if __name__ == "__main__":
    unittest.main()
