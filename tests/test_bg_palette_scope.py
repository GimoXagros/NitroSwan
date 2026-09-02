"""Source-contract checks for the upstream BG-only patch."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BgPaletteScope(unittest.TestCase):
    def test_hardware_selection_without_title_identity(self):
        code = (ROOT / "source/PaletteRaster.c").read_text(encoding="utf-8")
        self.assertIn("header != NULL && gSOC != SOC_ASWAN", code)
        for token in ("isOnePiece", "GameIdentity", "publisher", "checksum"):
            self.assertNotIn(token, code)

    def test_bounded_bg_only_replay(self):
        code = (ROOT / "source/PaletteRaster.c").read_text(encoding="utf-8")
        for token in ("WS_BG_COLORS 128", "MAX_BG_PALETTE_DELTAS 384",
                      "PALETTE_FRAME_COUNT 3", "appendDelta(line + 1"):
            self.assertIn(token, code)
        for token in ("ObjTileBuffer", "SPRITE_PALETTE", "DMA3"):
            self.assertNotIn(token, code)
        gfx = (ROOT / "source/Gfx.s").read_text(encoding="utf-8")
        self.assertIn("EMUPALBUFF:\n\t.space 0x400", gfx)
        self.assertFalse((ROOT / "source/ObjTileBuffer.c").exists())

    def test_palette_write_preserves_memory_write_registers(self):
        code = (ROOT / "source/Memory.s").read_text(encoding="utf-8")
        hook = code[code.index("paletteRamWriteNotify:"):code.index("cart_WW:")]
        self.assertIn("cmp r0,#0x0FE00000", hook)
        self.assertIn("stmfd sp!,{r0,r1,lr}", hook)
        self.assertIn("ldmfd sp!,{r0,r1,pc}", hook)


if __name__ == "__main__":
    unittest.main()
