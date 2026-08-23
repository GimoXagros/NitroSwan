#!/usr/bin/env python3
"""Source regressions for the project-local DSpico ROM bank cache."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DspicoRomCacheTests(unittest.TestCase):
    def test_shared_library_keeps_the_blocksds_mpu_layout(self):
        asm = (ROOT / "source" / "Shared" / "AsmExtra.s").read_text(encoding="utf-8")
        header = (ROOT / "source" / "Shared" / "AsmExtra.h").read_text(encoding="utf-8")
        cart = (ROOT / "source" / "Shared" / "CartridgeRAM.c").read_text(encoding="utf-8")
        self.assertNotIn("enableN3dsExtraCache", asm + header + cart)
        self.assertNotIn("disableN3dsExtraCache", asm + header + cart)

    def test_cache_is_dspico_only_and_does_not_replace_mem_aliases(self):
        files = (ROOT / "source" / "FileHandling.c").read_text(encoding="utf-8")
        wscart = (ROOT / "source" / "WSCart" / "WSCart.s").read_text(encoding="utf-8")
        cache = (ROOT / "source" / "DspicoRomCache.c").read_text(encoding="utf-8")
        self.assertIn("#ifdef DSPICO_3DS_BUILD", files)
        self.assertIn("expansionType == N3DS_RAM", files)
        self.assertIn("dspicoRomCacheInit", files)
        self.assertIn("#ifdef DSPICO_3DS_BUILD", wscart)
        self.assertIn("dspicoRomCacheMap", wscart)
        self.assertNotIn("memCached(", cache)
        self.assertNotIn("memUncached(", cache)

    def test_flash_writes_are_synchronized(self):
        flash = (ROOT / "source" / "WSCart" / "FlashMemory.s").read_text(encoding="utf-8")
        self.assertGreaterEqual(flash.count("dspicoRomCacheWriteBack"), 4)


if __name__ == "__main__":
    unittest.main()
