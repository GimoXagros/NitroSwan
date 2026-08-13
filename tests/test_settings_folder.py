#!/usr/bin/env python3
"""Settings-folder creation and hidden-folder access regressions."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SettingsFolderTests(unittest.TestCase):
    def test_missing_folder_is_created_at_root(self):
        helper = (ROOT / "source/Shared/FileHelper.c").read_text(encoding="utf-8")
        self.assertIn("int ensureFolder(const char *folderName)", helper)
        ensure = helper[helper.index("int ensureFolder("):helper.index("void getFileExtension(")]
        self.assertIn('chdir("/")', ensure)
        self.assertIn("mkdir(folderName, 0777)", ensure)
        self.assertIn("chdir(folderName)", ensure)

    def test_hidden_folder_is_opened_by_direct_path(self):
        helper = (ROOT / "source/Shared/FileHelper.c").read_text(encoding="utf-8")
        lookup = helper[helper.index("static int tryFindFolder("):helper.index("int findFolder(")]
        self.assertIn("chdir(folderName)", lookup)
        self.assertNotIn("ATTR_HIDDEN", lookup)
        self.assertNotIn("readdir", lookup)

    def test_first_launch_writes_default_binary_settings(self):
        handling = (ROOT / "source/FileHandling.c").read_text(encoding="utf-8")
        load = handling[handling.index("int loadSettings()"):handling.index("int saveSettings()")]
        self.assertIn("ensureFolder(folderName)", load)
        self.assertIn('fopen(settingName, "wb")', load)
        self.assertIn("fwrite(&cfg, 1, sizeof(ConfigData), file)", load)

    def test_direct_launch_path_is_resolved_before_settings_io(self):
        main = (ROOT / "source/Main.c").read_text(encoding="utf-8")
        resolve_call = main.index("launchGame = resolveLaunchPath(")
        settings_call = main.index("loadSettings();")
        eeprom_call = main.index("loadIntEeproms();")
        game_call = main.index("loadGame(launchGame);")
        self.assertLess(resolve_call, settings_call)
        self.assertLess(resolve_call, eeprom_call)
        self.assertLess(eeprom_call, game_call)
        resolver = main[main.index("static const char *resolveLaunchPath(", main.index("return 0;")):
                        main.index("void pausVBlank")]
        self.assertIn("getcwd(launchDirectory", resolver)
        self.assertIn("strchr(argument, ':')", resolver)
        self.assertIn("strchr(applicationPath, ':')", resolver)


if __name__ == "__main__":
    unittest.main()
