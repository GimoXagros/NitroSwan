#!/usr/bin/env python3
"""Regression checks for the stable custom graphics and One Piece path."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class GraphicsCoreTests(unittest.TestCase):
    def test_one_piece_raster_path_is_bounded_and_title_specific(self):
        video = (ROOT / "source" / "Sphinx" / "WSVideo.s").read_text(encoding="utf-8")
        raster = (ROOT / "source" / "PaletteRaster.c").read_text(encoding="utf-8")
        header = (ROOT / "source" / "PaletteRaster.h").read_text(encoding="utf-8")
        memory = (ROOT / "source" / "Memory.s").read_text(encoding="utf-8")
        self.assertIn("MAX_BG_PALETTE_DELTAS 384", raster)
        self.assertIn("PALETTE_FRAME_COUNT 3", raster)
        self.assertIn("header->gameId == 0x29", raster)
        self.assertIn("header->checksum == 0xFD2E", raster)
        self.assertIn("PALETTE_RASTER_CAPTURE_ONLY 1", header)
        self.assertIn("PALETTE_RASTER_REPLAY_ONLY 2", header)
        self.assertIn("PALETTE_RASTER_BG_ONLY 3", header)
        self.assertNotIn("SPRITE_PALETTE", raster)
        self.assertNotIn("DMA3", raster)
        self.assertNotIn("paletteRaster", memory)
        self.assertIn("onePieceVideoFixEnabled", video)

    def test_palette_and_obj_buffers_keep_the_release_contracts(self):
        gfx = (ROOT / "source" / "Gfx.s").read_text(encoding="utf-8")
        video = (ROOT / "source" / "Sphinx" / "WSVideo.s").read_text(encoding="utf-8")
        frame = gfx[gfx.index("gfxEndFrame:"):gfx.index("frameTotal:")]
        self.assertEqual(frame.count("bl paletteTxAll"), 1)
        self.assertIn("EMUPALBUFF:\n\t.space 0x400", gfx)
        self.assertIn("eor r0,r1,#0x200", video)
        self.assertIn("mov r2,#0x4000", video)
        self.assertIn("bleq dmaSprites", video)
        self.assertIn("drawFrameGfxAtVBlank", video)
        self.assertNotIn("PALETTE_RASTER_NO_FRAME_CALL", gfx)


if __name__ == "__main__":
    unittest.main()
