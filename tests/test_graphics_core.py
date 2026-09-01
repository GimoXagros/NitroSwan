#!/usr/bin/env python3
"""Regression checks for the generic WonderSwan video core path."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class GraphicsCoreTests(unittest.TestCase):
    def test_color_raster_path_is_bounded_and_hardware_selected(self):
        video = (ROOT / "source" / "Sphinx" / "WSVideo.s").read_text(encoding="utf-8")
        raster = (ROOT / "source" / "PaletteRaster.c").read_text(encoding="utf-8")
        header = (ROOT / "source" / "PaletteRaster.h").read_text(encoding="utf-8")
        memory = (ROOT / "source" / "Memory.s").read_text(encoding="utf-8")
        self.assertIn("MAX_BG_PALETTE_DELTAS 384", raster)
        self.assertIn("PALETTE_FRAME_COUNT 3", raster)
        self.assertIn("#define WS_BG_COLORS 256", raster)
        self.assertIn("header != NULL && gSOC != SOC_ASWAN", raster)
        self.assertNotIn("GameIdentity", raster)
        self.assertNotIn("publisher", raster)
        self.assertNotIn("gameId", raster)
        self.assertNotIn("checksum", raster)
        self.assertIn("PALETTE_RASTER_CAPTURE_ONLY 1", header)
        self.assertIn("PALETTE_RASTER_REPLAY_ONLY 2", header)
        self.assertIn("PALETTE_RASTER_BG_ONLY 3", header)
        self.assertNotIn("SPRITE_PALETTE", raster)
        self.assertNotIn("DMA3", raster)
        self.assertIn("cmp r0,#0x0FE00000", memory)
        self.assertIn("bl paletteRasterCapturePaletteWrite", memory)
        self.assertIn("objTileBufferBeginFrame", video)
        self.assertIn("latchSpritesForFrame", video)
        self.assertIn("#ifdef WS_VIDEO_WRITE_CALLBACK", video)
        self.assertIn("bl wsvVideoRegisterWriteCallback", video)
        self.assertNotIn("bl paletteRasterCaptureLine", video)

    def test_backdrop_uses_palette_zero_without_indexing_palette_ram_zero(self):
        raster = (ROOT / "source" / "PaletteRaster.c").read_text(encoding="utf-8")
        self.assertIn("previousBackdrop = backdropRawColor(palette);", raster)
        self.assertIn("appendDelta(line + 1, 0, backdrop);", raster)
        self.assertIn("if (index == sphinx0.bgColor)", raster)
        self.assertIn(
            "for (unsigned int index = 1; index < WS_BG_COLORS; index++)", raster
        )
        self.assertIn(
            "for (unsigned int index = 0; index < WS_BG_COLORS; index++)", raster
        )

        capture = raster[
            raster.index("void paletteRasterCapturePaletteWrite") :
            raster.index("void wsvVideoRegisterWriteCallback")
        ]
        self.assertNotIn("for (unsigned int index", capture)

    def test_write_time_capture_is_palette_bounded_and_preserves_write_contract(self):
        memory = (ROOT / "source" / "Memory.s").read_text(encoding="utf-8")
        hook = memory[memory.index("paletteRamWriteNotify:") : memory.index("cart_WW:")]
        self.assertIn("cmp r0,#0x0FE00000", hook)
        self.assertIn("bxcc lr", hook)
        self.assertIn("ldr r2,=wsvVideoWriteCallbackEnabled", hook)
        self.assertIn("stmfd sp!,{r0,r1,lr}", hook)
        self.assertIn("ldmfd sp!,{r0,r1,pc}", hook)
        self.assertEqual(hook.count("bl paletteRasterCapturePaletteWrite"), 1)

    def test_write_time_delta_model_coalesces_and_maps_to_next_line(self):
        capacity = 384
        events = []
        dropped = 0

        def append(line, index, color):
            nonlocal dropped
            for event in reversed(events):
                if event[0] != line:
                    break
                if event[1] == index:
                    event[2] = color
                    return
            if len(events) < capacity:
                events.append([line, index, color])
            else:
                dropped += 1

        # Two byte writes to one palette entry during WS line 12 become one
        # visible delta on line 13, with the final 12-bit value.
        append(12 + 1, 7, 0x034)
        append(12 + 1, 7, 0xA34)
        append(12 + 1, 0, 0x123)
        self.assertEqual(events, [[13, 7, 0xA34], [13, 0, 0x123]])

        for ws_line in range(13, 143):
            append(ws_line + 1, 1 + (ws_line % 127), ws_line & 0xFFF)
        self.assertEqual(dropped, 0)
        self.assertTrue(all(1 <= event[0] < 144 for event in events))

    def test_backdrop_event_model_is_bounded_and_preserves_scanline_order(self):
        capacity = 384
        previous = 0x001
        events = []
        dropped = 0
        for line in range(1, 144):
            backdrop = (line * 17) & 0xFFF
            if backdrop == previous:
                continue
            previous = backdrop
            if len(events) < capacity:
                events.append((line, 0, backdrop))
            else:
                dropped += 1

        self.assertEqual(len(events), 143)
        self.assertEqual(dropped, 0)
        self.assertEqual([event[0] for event in events], sorted(e[0] for e in events))
        self.assertTrue(all(event[1] == 0 for event in events))

        overflow_capacity = 8
        overflow_events = events[:overflow_capacity]
        overflow_dropped = len(events) - len(overflow_events)
        self.assertEqual(len(overflow_events), overflow_capacity)
        self.assertGreater(overflow_dropped, 0)

    def test_synthetic_palette_capture_and_replay_matches_ws_scanlines(self):
        ds_game_top = (192 - 144) // 2
        capacity = 384
        base = {0: 0x001, 1: 0x111, 2: 0x222}
        ws_changes = {
            3: {0: 0x123},
            27: {2: 0x456},
            91: {0: 0x789, 1: 0xABC},
        }
        events = []
        for line in range(144):
            for index, color in ws_changes.get(line, {}).items():
                if len(events) < capacity:
                    events.append((line, index, color))

        replay = dict(base)
        observed = {}
        cursor = 0
        for ws_line in range(144):
            while cursor < len(events) and events[cursor][0] == ws_line:
                _, index, color = events[cursor]
                replay[index] = color
                cursor += 1
            observed[ds_game_top + ws_line] = dict(replay)

        self.assertEqual(observed[24][0], 0x001)
        self.assertEqual(observed[27][0], 0x123)
        self.assertEqual(observed[51][2], 0x456)
        self.assertEqual(observed[115][0], 0x789)
        self.assertEqual(observed[115][1], 0xABC)
        self.assertEqual(cursor, len(events))

    def test_triple_buffer_ownership_never_reuses_active_or_ready(self):
        def next_free(active, ready):
            for index in range(3):
                if index != active and index != ready:
                    return index
            return 0

        for active in (-1, 0, 1, 2):
            for ready in (-1, 0, 1, 2):
                if active == ready and active >= 0:
                    continue
                capture = next_free(active, ready)
                self.assertNotEqual(capture, active)
                self.assertNotEqual(capture, ready)

    def test_vcount_mapping_and_vblank_base_restore_contracts(self):
        raster = (ROOT / "source" / "PaletteRaster.c").read_text(encoding="utf-8")
        main = (ROOT / "source" / "Main.c").read_text(encoding="utf-8")
        self.assertIn("#define DS_GAME_TOP ((SCREEN_HEIGHT - WS_VISIBLE_LINES) / 2)", raster)
        self.assertIn("SetYtrigger(DS_GAME_TOP + active->delta[0].line);", raster)
        self.assertIn("BG_PALETTE[index] = active->base[index];", raster)
        vblank = main[main.index("void myVblank(void)") : main.index("int main(")]
        self.assertLess(vblank.index("vblIrqHandler();"), vblank.index("paletteRasterVBlank();"))

    def test_palette_and_obj_buffers_keep_the_release_contracts(self):
        gfx = (ROOT / "source" / "Gfx.s").read_text(encoding="utf-8")
        video = (ROOT / "source" / "Sphinx" / "WSVideo.s").read_text(encoding="utf-8")
        obj = (ROOT / "source" / "ObjTileBuffer.c").read_text(encoding="utf-8")
        frame = gfx[gfx.index("gfxEndFrame:"):gfx.index("frameTotal:")]
        self.assertEqual(frame.count("bl paletteTxAll"), 1)
        self.assertIn("EMUPALBUFF:\n\t.space 0x400", gfx)
        self.assertIn("sourceOffset ^ 0x200", obj)
        self.assertIn("(format & 0xC0) == 0xC0", obj)
        self.assertIn("bits &= bits - 1", obj)
        self.assertNotIn("memCopy", obj)
        self.assertIn("cmp r1,#0x4000", video)
        self.assertIn("strcc r3,[r8,r1]", video)
        self.assertNotIn("onePiece", video)
        self.assertNotIn("bl dmaSprites", frame)
        self.assertIn("bl dmaSprites", video[video.index("latchSpritesForFrame:"):video.index("endFrame:")])
        self.assertIn("drawFrameGfxAtVBlank", video)
        self.assertNotIn("PALETTE_RASTER_NO_FRAME_CALL", gfx)
        self.assertIn("REG_DMA3CNT_H", gfx)
        self.assertIn("dmaWinInOut", gfx)
        self.assertIn("REG_WIN0H", gfx)

    def test_sparse_obj_generation_copy_preserves_unchanged_tiles(self):
        tile_count = 512
        bank = [[0] * tile_count, [0] * tile_count]
        current_bank = 0
        previous_dirty = set(range(tile_count))

        def commit(changes):
            nonlocal current_bank, previous_dirty
            if not changes:
                return 0
            next_bank = current_bank ^ 1
            for tile in previous_dirty:
                bank[next_bank][tile] = bank[current_bank][tile]
            for tile, value in changes.items():
                bank[next_bank][tile] = value
            current_bank = next_bank
            copied = len(previous_dirty) * 32
            previous_dirty = set(changes)
            return copied

        self.assertEqual(commit({2: 20, 400: 40}), 512 * 32)
        self.assertEqual(bank[current_bank][2], 20)
        self.assertEqual(commit({7: 70}), 2 * 32)
        self.assertEqual(bank[current_bank][2], 20)
        self.assertEqual(bank[current_bank][400], 40)
        self.assertEqual(bank[current_bank][7], 70)
        old_bank = current_bank
        self.assertEqual(commit({}), 0)
        self.assertEqual(current_bank, old_bank)


if __name__ == "__main__":
    unittest.main()
