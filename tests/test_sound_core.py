#!/usr/bin/env python3
"""Regression checks for the stable custom audio path."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SoundCoreTests(unittest.TestCase):
    def test_scanline_mixer_uses_the_known_good_two_sample_path(self):
        sound = (ROOT / "source/Sound.s").read_text(encoding="utf-8")
        video = (ROOT / "source/Sphinx/WSVideo.s").read_text(encoding="utf-8")
        scanline_audio = video[video.index("wsvDoScanline:"):video.index("checkSerialRxTx:")]
        self.assertEqual(scanline_audio.count("bl soundUpdate"), 1)
        update = sound[sound.index("soundUpdate:"):sound.index("sndWritePtr:")]
        self.assertIn("mov r0,#2", update)
        self.assertIn("b wsAudioMixer", update)
        self.assertNotIn("soundDiscardPair", sound)

    def test_unverified_audio_rework_is_not_linked(self):
        audio = (ROOT / "source/Sphinx/WSAudio.s").read_text(encoding="utf-8")
        video = (ROOT / "source/Sphinx/WSVideo.s").read_text(encoding="utf-8")
        self.assertNotIn("wsvHyperDirectW", video)
        self.assertNotIn("wsaSetHyperVoiceValueStereo", audio)


if __name__ == "__main__":
    unittest.main()
