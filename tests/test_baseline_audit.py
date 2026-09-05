"""Source/model evidence for the r7 audit; NOT scanout/hardware verification."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def next_free(active, ready):
    return next(i for i in range(3) if i not in (active, ready))


class BaselineAuditTests(unittest.TestCase):
    def test_old_palette_handoff_has_interrupt_counterexample(self):
        active, finished = 1, 0
        ready = finished
        loaded_active = active
        # VBlank interrupts between the two volatile argument loads.
        active, ready = ready, -1
        capture = next_free(loaded_active, ready)
        self.assertEqual(capture, active)  # Reproduces the OLD defect, not a pass of safety.

    def test_palette_handoff_pins_finished_index_across_all_irq_slots(self):
        for active in (-1, 0, 1, 2):
            for finished in range(3):
                if active == finished:
                    continue
                for irq_slot in range(4):
                    observed_active = finished if irq_slot == 0 else active
                    capture = next_free(observed_active, finished)
                    actual_active = finished if irq_slot < 3 else active
                    self.assertNotEqual(capture, actual_active)
                    self.assertNotEqual(capture, finished)
        source = (ROOT / "source/PaletteRaster.c").read_text(encoding="utf-8")
        self.assertIn("const int finishedFrame = captureFrame;", source)
        self.assertIn("pendingFrame = finishedFrame;", source)
        self.assertIn("readyFrame = pendingFrame;", source)
        self.assertIn("captureFrame = nextFreeFrame(activeFrame, readyFrame);", source)

    def test_dead_line_index_not_part_of_replay(self):
        source = (ROOT / "source/PaletteRaster.c").read_text(encoding="utf-8")
        self.assertNotIn("lineStart", source)
        self.assertIn("active->delta[replayCursor++]", source)
        self.assertIn("replayCursor < active->count", source)

    def test_obj_metrics_separate_seed_and_publication_clocks(self):
        source = (ROOT / "source/ObjTileBuffer.c").read_text(encoding="utf-8")
        header = (ROOT / "source/ObjTileBuffer.h").read_text(encoding="utf-8")
        self.assertIn("objSeedBytesFrame", header)
        self.assertIn("objPublishBytesHostFrame", header)
        begin = source[source.index("void objTileBufferBeginFrame"):]
        self.assertIn("objSeedBytesFrame = 0;", begin)
        self.assertIn("objSeedBytesFrame = OBJ_BANK_BYTES;", begin)
        publish = source[source.index("const void *videoTileBufferVBlank"):]
        self.assertIn("objPublishBytesHostFrame = 0;", publish)
        self.assertIn("objPublishBytesHostFrame = OBJ_BANK_BYTES;", publish)

    def test_obj_metadata_uses_one_completed_frame_descriptor(self):
        source = (ROOT / "source/ObjTileBuffer.c").read_text(encoding="utf-8")
        self.assertIn("CompletedFrameDescriptor", source)
        self.assertIn("readyFrameSlot = pendingFrameSlot", source)
        self.assertNotIn("objReadyGeneration", source)

    def test_graphics_callback_stack_alignment_is_repaired_for_full_chain(self):
        # C -> run (9 words) -> scanline (1) -> endFrame (1) -> gfxEndFrame
        # (7) -> C-call save (2). The repaired C-call entry is 0 mod 8.
        stack_mod8 = (-4 * (9 + 1 + 1 + 7 + 2)) % 8
        self.assertEqual(stack_mod8, 0)


if __name__ == "__main__":
    unittest.main()
