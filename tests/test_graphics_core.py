#!/usr/bin/env python3
"""Regression checks for the stable custom graphics path."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class GraphicsCoreTests(unittest.TestCase):
    def test_experimental_raster_path_is_not_in_the_release(self):
        video = (ROOT / "source" / "Sphinx" / "WSVideo.s").read_text(encoding="utf-8")
        main = (ROOT / "source" / "Main.c").read_text(encoding="utf-8")
        self.assertNotIn("paletteRaster", video)
        self.assertNotIn("IRQ_HBLANK", main)
        self.assertFalse((ROOT / "source" / "PaletteRaster.c").exists())

    def test_palette_transfer_stays_on_the_known_good_frame_boundary(self):
        gfx = (ROOT / "source" / "Gfx.s").read_text(encoding="utf-8")
        video = (ROOT / "source" / "Sphinx" / "WSVideo.s").read_text(encoding="utf-8")
        frame = gfx[gfx.index("gfxEndFrame:"):gfx.index("frameTotal:")]
        self.assertEqual(frame.count("bl paletteTxAll"), 1)
        self.assertIn("newFrame:", video)
        self.assertIn("newFrame:\t\t\t\t\t;@ Called before line 0\n;@----------------------------------------------------------------------------\n\tbx lr", video)


if __name__ == "__main__":
    unittest.main()
