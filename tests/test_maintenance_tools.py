"""Host tooling tests (not emulator or console hardware evidence)."""

import contextlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools import run_core_regressions as runner
from tools import validate_repository as hygiene


class CompilerTests(unittest.TestCase):
    @patch.dict(os.environ, {"HOST_CC": "preferred", "CC": "last"}, clear=True)
    def test_host_cc_first(self):
        with patch.object(runner.shutil, "which", side_effect=lambda s: s), \
                patch.object(runner, "probe_host_compiler", return_value=True) as probe:
            self.assertEqual(runner.find_c_compiler(), "preferred")
            probe.assert_called_once_with("preferred")

    @patch.dict(os.environ, {"HOST_CC": "cross", "CC": "last"}, clear=True)
    def test_reject_cross_and_preserve_path_order(self):
        with patch.object(runner.shutil, "which", side_effect=lambda s: s), \
                patch.object(runner, "probe_host_compiler",
                             side_effect=[False, False, False, False, True]) as probe:
            self.assertEqual(runner.find_c_compiler(), "last")
            self.assertEqual([c.args[0] for c in probe.call_args_list],
                             ["cross", "cc", "gcc", "clang", "last"])

    def test_probe_must_execute_and_match_output(self):
        with patch.object(runner.subprocess, "run", side_effect=[
                subprocess.CompletedProcess([], 0), OSError("wrong architecture")]):
            self.assertFalse(runner.probe_host_compiler("cross"))
        with patch.object(runner.subprocess, "run", return_value=
                          subprocess.CompletedProcess([], 0, stdout="wrong")):
            self.assertFalse(runner.probe_host_compiler("stub"))
        with patch.object(runner.subprocess, "run", return_value=
                          subprocess.CompletedProcess([], 0, stdout="nitroswan-host-probe\n")):
            self.assertTrue(runner.probe_host_compiler("host"))

    def test_probe_timeout_is_rejected(self):
        with patch.object(runner.subprocess, "run", side_effect=
                          subprocess.TimeoutExpired("compiler", 30)):
            self.assertFalse(runner.probe_host_compiler("hung"))

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_compiler_is_explicit_skip_not_host_pass(self):
        output = io.StringIO()
        with patch.object(runner, "run"), \
                patch.object(runner, "find_c_compiler", return_value=None), \
                contextlib.redirect_stdout(output):
            self.assertEqual(runner.main(), 0)
        self.assertIn("SKIP host C regressions", output.getvalue())
        self.assertNotIn("PASS host C", output.getvalue())

    @patch.dict(os.environ, {"REQUIRE_HOST_CC": "1"}, clear=True)
    def test_ci_requires_real_host_tests(self):
        with patch.object(runner, "run"), \
                patch.object(runner, "find_c_compiler", return_value=None), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runner.main(), 1)


class RepositoryTests(unittest.TestCase):
    def test_ci_trusts_only_its_checkout(self):
        workflow = (hygiene.ROOT / ".github/workflows/build.yaml").read_text(
            encoding="utf-8")
        trust_lines = [line.strip() for line in workflow.splitlines()
                       if "git config" in line and "safe.directory" in line]
        self.assertEqual(trust_lines, [
            'git config --global --add safe.directory "$GITHUB_WORKSPACE"'])

    def test_ci_validates_renderer_abi_for_ds_and_dsi(self):
        workflow = (hygiene.ROOT / ".github/workflows/build.yaml").read_text(
            encoding="utf-8")
        self.assertEqual(workflow.count("tools/validate_renderer_abi.py"), 2)
        for name in ("NitroSwan-DS-0.7.7-custom.r8",
                     "NitroSwan-DSi-0.7.7-custom.r8"):
            self.assertIn(f"--build-dir build/{name}", workflow)

    def test_personal_paths_and_narrow_example_allowlist(self):
        # Construct forbidden samples so the test itself contains no private path.
        for path in ("C:" + "/Users/" + "alice/sdk", "/home/" + "alice/sdk",
                     "C:" + "\\Users\\" + "alice\\sdk"):
            self.assertTrue(hygiene.check_text("tools/x.py", path, set()))
        example = "/home/" + "example/sdk"
        self.assertFalse(hygiene.check_text("Docs/DevelopmentGuide.md", example, set()))
        self.assertTrue(hygiene.check_text("tools/x.py", example, set()))

    def test_conflicts_not_document_separators(self):
        self.assertFalse(hygiene.check_text("doc", "=======\n================", set()))
        for prefix in ("<", ">", "|"):
            self.assertTrue(hygiene.check_text("doc", prefix * 7 + " branch", set()))

    def test_stale_test_and_module_reference(self):
        missing = "tests/" + "test_missing.py"
        self.assertTrue(hygiene.check_text("tools/run.py", missing, set()))
        self.assertFalse(hygiene.check_text("tools/run.py", missing, {missing}))
        self.assertFalse(hygiene.check_text("Docs/old.md", missing, set()))
        module = "tests." + "test_missing"
        self.assertTrue(hygiene.check_text(".github/workflows/x.yaml", module, set()))

    def test_private_build_binary_mode_case_and_missing_documents(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = []
            for name in ("game.sav", "game.rom", "unknown.bin", "output.nds", "file.c"):
                (root / name).write_text("int x;\n", encoding="utf-8")
                records.append(("100755" if name == "file.c" else "100644", name))
            records.append(("100644", "FILE.c"))
            errors = "\n".join(hygiene.validate(root, records))
            for expected in ("private test", "generated build", "unreviewed binary",
                             "executable bit", "case collision", "required tracked"):
                self.assertIn(expected, errors)

    def test_current_versions_only(self):
        texts = {name: (hygiene.ROOT / name).read_text(encoding="utf-8")
                 for name in ("README.md", "source/Gui.c", ".github/workflows/build.yaml")}
        self.assertEqual(hygiene.check_versions(texts), [])
        texts["History.txt"] = "V0.7.7-custom.r2\nWSC-VideoCore-r8-test"
        self.assertEqual(hygiene.check_versions(texts), [])
        texts[".github/workflows/build.yaml"] = texts[
            ".github/workflows/build.yaml"].replace("custom.r8", "custom.r9")
        self.assertTrue(hygiene.check_versions(texts))


if __name__ == "__main__":
    unittest.main()
