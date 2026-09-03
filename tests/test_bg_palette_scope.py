"""Source/model checks for the upstream BG-only patch, not hardware tests."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BgPaletteScope(unittest.TestCase):
    def test_old_handoff_has_interrupt_counterexample(self):
        active, finished = 1, 0
        ready = finished
        loaded_active = active
        # VBlank between the two volatile argument loads consumes ready.
        active, ready = ready, -1
        capture = next(i for i in range(3) if i not in (loaded_active, ready))
        self.assertEqual(capture, active)  # OLD failure, not proof of safety.

    def test_finished_slot_is_excluded_across_handoff_interrupts(self):
        for active in (-1, 0, 1, 2):
            for finished in range(3):
                if active == finished:
                    continue
                for before_active_load in (False, True):
                    observed_active = finished if before_active_load else active
                    capture = next(i for i in range(3)
                                   if i not in (observed_active, finished))
                    # A subsequent VBlank can only retain active or consume
                    # this finished slot. Neither may be the new writer.
                    self.assertNotEqual(capture, finished)
                    if not before_active_load:
                        self.assertNotEqual(capture, active)
        code = (ROOT / "source/PaletteRaster.c").read_text(encoding="utf-8")
        self.assertIn("const int finishedFrame = captureFrame;", code)
        self.assertIn("readyFrame = finishedFrame;", code)
        self.assertIn("nextFreeFrame(activeFrame, finishedFrame)", code)
        self.assertNotIn("nextFreeFrame(activeFrame, readyFrame)", code)

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
