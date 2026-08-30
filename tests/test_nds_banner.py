#!/usr/bin/env python3
"""Keep the NitroSwan logo wired into generated NDS banners."""

from pathlib import Path
import struct
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NdsBannerTests(unittest.TestCase):
    def test_makefile_uses_the_existing_logo(self):
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("GAME_ICON\t:= WSLogo.bmp", makefile)
        self.assertIn("-b $(GAME_ICON) \"$(GAME_FULL_TITLE)\"", makefile)

    def test_logo_is_a_nonempty_32_by_32_bitmap(self):
        data = (ROOT / "WSLogo.bmp").read_bytes()
        self.assertEqual(data[:2], b"BM")
        width, height = struct.unpack_from("<ii", data, 18)
        bits_per_pixel = struct.unpack_from("<H", data, 28)[0]
        pixel_offset = struct.unpack_from("<I", data, 10)[0]
        self.assertEqual((width, abs(height)), (32, 32))
        self.assertIn(bits_per_pixel, (4, 8, 24, 32))
        self.assertGreater(len(data), pixel_offset)
        self.assertNotEqual(set(data[pixel_offset:]), {0})


if __name__ == "__main__":
    unittest.main()
