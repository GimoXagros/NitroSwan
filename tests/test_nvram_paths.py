import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NvramPathTests(unittest.TestCase):
    def test_loaded_rom_path_is_reduced_to_filename(self):
        helper = (ROOT / "source/Shared/FileHelper.c").read_text(encoding="utf-8")
        self.assertIn("static void rememberLoadedFilename", helper)
        self.assertIn("strrchr(fileName, '/')", helper)
        self.assertIn("rememberLoadedFilename(fileName);", helper)

    def test_nvram_io_is_binary_and_uses_save_folder(self):
        handling = (ROOT / "source/FileHandling.c").read_text(encoding="utf-8")
        self.assertIn("findFolder(folderName)", handling)
        self.assertIn('fopen(nvRamName, "rb")', handling)
        self.assertIn('fopen(nvRamName, "wb")', handling)
        self.assertIn('setFileExtension(nvRamName, currentFilename, ".sav"', handling)

    def test_nvram_autosave_is_default_migrated_and_visible(self):
        handling = (ROOT / "source/FileHandling.c").read_text(encoding="utf-8")
        gui = (ROOT / "source/Gui.c").read_text(encoding="utf-8")
        menu = (ROOT / "source/Shared/EmuMenu.c").read_text(encoding="utf-8")
        self.assertIn("AUTOLOAD_NVRAM | AUTOSAVE_NVRAM", handling)
        self.assertIn("cfg.emuSettings |= AUTOSAVE_NVRAM", handling)
        self.assertIn('{"Autosave NVRAM:", saveNVRAMSet, getSaveNVRAMText}', gui)
        self.assertIn("gameInserted && (emuSettings & AUTOSAVE_NVRAM)", menu)


if __name__ == "__main__":
    unittest.main()
