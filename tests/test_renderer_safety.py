"""Renderer safety source/model tests; not emulator or hardware validation."""

from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_trace_analyzer():
    path = ROOT / "tools/analyze_renderer_trace.py"
    spec = importlib.util.spec_from_file_location("trace_analyzer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PublicationModel:
    def __init__(self):
        self.ready = None
        self.published = None

    def complete(self, frame, oam, obj_bank, obj_generation, bg_bank):
        # Models the short metadata-only IRQ critical section.
        self.ready = (frame, oam, obj_bank, obj_generation, bg_bank)

    def vblank(self):
        if self.ready and (
                self.published is None or self.ready[0] != self.published[0]):
            self.published = self.ready
        return self.published

    def quiesce(self):
        self.ready = None
        self.published = None


class RendererSafetyTests(unittest.TestCase):
    def test_all_renderer_c_call_sites_are_eight_byte_aligned(self):
        gfx = (ROOT / "source/Gfx.s").read_text(encoding="utf-8")
        memory = (ROOT / "source/Memory.s").read_text(encoding="utf-8")
        video = (ROOT / "source/Sphinx/WSVideo.s").read_text(encoding="utf-8")

        refresh = gfx[gfx.index("gfxRefresh:"):gfx.index("gfxEndFrame:")]
        frame = gfx[gfx.index("gfxEndFrame:"):gfx.index("frameTotal:")]
        self.assertIn("stmfd sp!,{lr}", refresh)
        self.assertIn("bl gfxEndFrame", refresh)
        rebuild = gfx[gfx.index("gfxRebuildRendererState:"):
                      gfx.index("gfxEndFrame:")]
        self.assertIn("stmfd sp!,{r4-r10,lr}", rebuild)
        self.assertNotIn("updateSlowIO", rebuild)
        self.assertNotIn("frameTotal", rebuild)
        self.assertIn("stmfd sp!,{r4-r9,lr}", frame)
        self.assertIn("stmfd sp!,{spxptr,lr}", frame)

        unaligned = memory[memory.index("cpuWriteWordUnaligned:"):
                           memory.index("v30WriteEA:")]
        callback = memory[memory.index("paletteRamWriteNotify:"):
                          memory.index("cart_WW:")]
        self.assertIn("stmfd sp!,{r2,lr}", unaligned)
        self.assertIn("ldmfd sp!,{r2,lr}", unaligned)
        self.assertIn("stmfd sp!,{r0-r2,lr}", callback)
        self.assertIn("ldmfd sp!,{r0-r2,pc}", callback)

        word_write = video[video.index("wsvWrite16:"):
                           video.index("wsvWrite:")]
        register = video[video.index("wsvBgColorW:"):
                         video.index("wsvSpriteTblAdrW:")]
        self.assertIn("stmfd sp!,{r0,r1,spxptr,lr}", word_write)
        self.assertIn("ldmfd sp!,{r0,r1,spxptr,lr}", word_write)
        self.assertIn("stmfd sp!,{r0-r3,spxptr,lr}", register)

        # C entry=0. run(9)=4, wsvDoScanline(1)=0, endFrame(1)=4,
        # gfxEndFrame(7)=0, C save(2)=0.
        self.assertEqual((-4 * (9 + 1 + 1 + 7 + 2)) % 8, 0)
        # V30 dispatcher has one word. Byte and normalized word writes enter
        # callbacks at 0; the callback's four-word save preserves alignment.
        self.assertEqual((-4 * (9 + 1 + 4)) % 8, 0)

    def test_restore_is_quiesce_rebuild_commit(self):
        code = (ROOT / "source/WonderSwan.c").read_text(encoding="utf-8")
        body = code[code.index("void unpackState"):code.index("int getStateSize")]
        ordered = [
            "paletteRasterPrepareStateRestore();",
            "sphinxLoadState(",
            "objTileBufferCompleteStateRestore(",
            "paletteRasterCompleteStateRestore(",
            "gfxRebuildRendererState();",
        ]
        positions = [body.index(token) for token in ordered]
        self.assertEqual(positions, sorted(positions))
        gfx = (ROOT / "source/Gfx.s").read_text(encoding="utf-8")
        for body in (
                gfx[gfx.index("gfxRebuildRendererState:"):
                    gfx.index("gfxEndFrame:")],
                gfx[gfx.index("gfxEndFrame:"):gfx.index("frameTotal:")]):
            self.assertLess(body.index("videoTileBufferFrameComplete"),
                            body.index("paletteRasterFrameComplete"))
            self.assertLess(body.index("paletteRasterFrameComplete"),
                            body.index("videoTileBufferFrameCommit"))
            self.assertLess(body.index("videoTileBufferFrameCommit"),
                            body.index("paletteRasterBeginFrame"))

    def test_reset_and_rom_switch_quiesce_before_machine_reset(self):
        gui = (ROOT / "source/Gui.c").read_text(encoding="utf-8")
        reset_start = gui.index("void resetGame() {")
        reset = gui[reset_start:gui.index("void updateGameId", reset_start)]
        self.assertLess(reset.index("paletteRasterPrepareStateRestore();"),
                        reset.index("loadCart();"))
        files = (ROOT / "source/FileHandling.c").read_text(encoding="utf-8")
        load_start = files.index("bool loadGame(const char *gameName) {")
        load = files[load_start:files.index("void selectGame", load_start)]
        self.assertLess(load.index("paletteRasterPrepareStateRestore();"),
                        load.index("loadCart();"))

    def test_descriptor_never_mixes_oam_tiles_or_bg(self):
        model = PublicationModel()
        model.complete(7, "oam7", 0, 11, 0x0000)
        # A later completed WS frame replaces the whole descriptor atomically.
        model.complete(8, "oam8", 512, 12, 0x8000)
        self.assertEqual(model.vblank(), (8, "oam8", 512, 12, 0x8000))
        model.quiesce()
        self.assertIsNone(model.vblank())

    def test_lifecycle_transitions_and_generation_wrap(self):
        transitions = (
            "load-before-vblank", "load-with-ready", "reset-before-vblank",
            "rom-a-to-rom-b", "color-to-mono", "4bpp-to-2bpp",
            "lcd-off-to-on", "repeated-load-reset",
        )
        for index, _name in enumerate(transitions, 1):
            model = PublicationModel()
            model.complete(index, f"old-oam-{index}", 0, index, 0)
            model.quiesce()
            self.assertIsNone(model.vblank())
            model.complete(index + 100, f"new-oam-{index}", 512,
                           index + 100, 0x8000)
            self.assertEqual(model.vblank()[0], index + 100)

        code = (ROOT / "source/ObjTileBuffer.c").read_text(encoding="utf-8")
        self.assertIn("return generation != 0 ? generation : 1;", code)

    def test_metadata_commit_is_short_and_reset_invalidates_first(self):
        code = (ROOT / "source/ObjTileBuffer.c").read_text(encoding="utf-8")
        complete = code[code.index("void videoTileBufferFrameComplete"):
                        code.index("const void *videoTileBufferVBlank")]
        self.assertIn("enterCriticalSection()", complete)
        self.assertIn("readyFrameSlot = pendingFrameSlot", complete)
        self.assertIn("paletteRasterCommitFrame();", complete)
        self.assertIn("memcpy(slot->oam, completedOam", complete)
        commit = complete[complete.index("void videoTileBufferFrameCommit"):]
        critical = commit[commit.index("const int oldIme"):]
        self.assertNotIn("memcpy", critical)
        reset = code[code.index("void objTileBufferReset"):
                     code.index("void objTileBufferBeginFrame")]
        self.assertLess(reset.index("objTileBufferQuiesce();"),
                        reset.index("memset(wsvObjTileSnapshots"))

    def test_obj_metrics_separate_ws_and_host_clock_domains(self):
        header = (ROOT / "source/ObjTileBuffer.h").read_text(encoding="utf-8")
        for token in (
                "objSeedBytesFrame", "objPublishBytesHostFrame",
                "objTotalBytes", "objTilesConvertedWSFrame",
                "objPublicationCount", "skippedCleanGenerationCount"):
            self.assertIn(token, header)

    def test_optional_runtime_abi_sentinel_and_trace_are_release_gated(self):
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        main = (ROOT / "source/Main.c").read_text(encoding="utf-8")
        sentinel = (ROOT / "source/RendererAbiSelfTest.s").read_text(
            encoding="utf-8")
        trace = (ROOT / "source/RendererTrace.c").read_text(encoding="utf-8")
        self.assertIn("ifeq ($(RENDERER_ABI_SELF_TEST),1)", makefile)
        self.assertIn("ifeq ($(WSC_VIDEO_TRACE),1)", makefile)
        self.assertIn("#ifdef RENDERER_ABI_SELF_TEST", main)
        self.assertIn("stmfd sp!,{r4-r11,lr}", sentinel)
        self.assertIn("sub sp,sp,#4", sentinel)
        self.assertIn("bl rendererAbiSentinelCallback", sentinel)
        self.assertIn("#ifdef WSC_VIDEO_TRACE", trace)
        self.assertNotIn("currentFilename", trace)
        self.assertNotIn("gGameHeader", trace)

    def test_trace_analyzer_detects_mixed_completed_frame(self):
        analyzer = load_trace_analyzer()
        base = {
            "event": "W", "seq": "1", "ws_frame": "8",
            "sprite_latch_frame": "8", "oam_frame": "7",
            "obj_ready_frame": "8", "obj_published_frame": "7",
            "obj_ready_tile_gen": "12", "obj_published_tile_gen": "11",
            "obj_dirty_tiles": "4", "obj_seed_bytes": "16384",
            "palette_drops": "0",
        }
        vblank = dict(base, event="V", seq="2", oam_frame="7",
                      obj_published_frame="8", obj_published_tile_gen="12")
        failed = analyzer.analyze([base, vblank])
        self.assertEqual(failed["status"], "FAIL")
        self.assertIn("oam-frame-mismatch",
                      {item["kind"] for item in failed["findings"]})
        vblank["oam_frame"] = "8"
        self.assertEqual(analyzer.analyze([base, vblank])["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
