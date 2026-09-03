#!/usr/bin/env python3
"""Validate tracked repository inputs, not ignored private assets or old releases."""

from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = "0.7.7-custom.r7"
REQUIRED_DOCS = (
    "README.md", "History.txt", "NitroSwan_todo.txt",
    "Docs/DevelopmentGuide.md", "Docs/BaselineAudit-r7.md",
    "Docs/ReleaseValidation-r7.md", "Docs/GameCompatibilityIdentity.md",
    "Docs/ROMFetchWaitstate.md",
)
PRIVATE_SUFFIXES = {
    ".ws", ".wsc", ".pc2", ".rom", ".bios", ".sav", ".srm",
    ".ram", ".eeprom", ".state", ".ss0", ".ss1", ".ss2",
}
BUILD_SUFFIXES = {".o", ".elf", ".nds", ".dsi", ".map", ".pyc", ".exe"}
# Exact, reviewed assets only: font data and Metis replacement IPLs, installed
# by upstream commit 5a21b47 and embedded by Cart.s (not commercial BIOS dumps).
ALLOWED_BINARIES = {
    "assets/fonts/cp949_table.bin", "assets/fonts/unicode_font.bin",
    "include/wsroms/ws_irom.bin", "include/wsroms/wc_irom.bin",
}
PERSONAL_PATH = re.compile(
    r"[A-Za-z]:[/\\]+Users[/\\]+[\w.-]+"
    r"|/home/[\w.-]+"
)
# Only these literal non-personal examples may occur in developer documents.
PATH_EXAMPLES = {"/home/" + "example", "C:/Users/" + "example"}
EXAMPLE_DOCS = {"Docs/DevelopmentGuide.md"}
CONFLICT = re.compile(r"^(?:<{7,}(?:\s.*)?|>{7,}(?:\s.*)?|\|{7,}(?:\s.*)?)$")
TEST_REFERENCE = re.compile(r"\btests/(?:[\w.-]+/)*test_[\w.-]+\.(?:py|c)\b")
MODULE_REFERENCE = re.compile(r"\btests\.(test_[A-Za-z0-9_]+)\b")


def tracked_files(root: Path) -> list[tuple[str, str]]:
    result = subprocess.run(
        ["git", "ls-files", "--stage", "--recurse-submodules", "-z"],
        cwd=root, check=True, capture_output=True,
    )
    records = []
    for entry in result.stdout.decode("utf-8").split("\0"):
        if entry:
            metadata, name = entry.split("\t", 1)
            mode, _, stage = metadata.split()
            if stage != "0":
                raise ValueError(f"Unmerged index entry: {name}")
            records.append((mode, name))
    return records


def check_text(name: str, content: str, names: set[str]) -> list[str]:
    errors = []
    for line_number, line in enumerate(content.splitlines(), 1):
        # A standalone ======= heading is not a conflict. Start/end/base
        # markers are checked independently, including incomplete conflicts.
        if CONFLICT.fullmatch(line):
            errors.append(f"{name}:{line_number}: merge conflict marker")
        for match in PERSONAL_PATH.finditer(line):
            if name not in EXAMPLE_DOCS or match.group() not in PATH_EXAMPLES:
                errors.append(f"{name}:{line_number}: personal absolute path")
    # Old release/audit prose is historical evidence, not an executable test list.
    if name.startswith(("tools/", "tests/", ".github/")):
        references = set(TEST_REFERENCE.findall(content))
        references.update(f"tests/{module}.py"
                          for module in MODULE_REFERENCE.findall(content))
        for reference in sorted(references - names):
            errors.append(f"{name}: stale test reference {reference}")
    return errors


def check_versions(texts: dict[str, str]) -> list[str]:
    errors = []
    readme = texts.get("README.md", "")
    if readme.splitlines()[:1] != [f"# NitroSwan V{CURRENT_VERSION}"]:
        errors.append("README.md: current title version mismatch")
    gui = texts.get("source/Gui.c", "")
    if not re.search(r'#define\s+EMUVERSION\s+"V' + re.escape(CURRENT_VERSION)
                     + r' \d{4}-\d{2}-\d{2}"', gui):
        errors.append("source/Gui.c: EMUVERSION mismatch")
    workflow = texts.get(".github/workflows/build.yaml", "")
    for name, content in (("README.md", readme),
                          (".github/workflows/build.yaml", workflow)):
        builds = re.findall(r"NAME=(NitroSwan-[A-Za-z0-9.-]+)", content)
        expected = {f"NitroSwan-DS-{CURRENT_VERSION}",
                    f"NitroSwan-DSi-{CURRENT_VERSION}"}
        if set(builds) != expected:
            errors.append(f"{name}: current build names mismatch")
    nds_names = set(re.findall(r"NitroSwan-DSi?-[\w.-]+\.nds", workflow))
    if nds_names != {f"NitroSwan-DS-{CURRENT_VERSION}.nds",
                     f"NitroSwan-DSi-{CURRENT_VERSION}.nds"}:
        errors.append("build.yaml: executable artifact names mismatch")
    if re.findall(r"name:\s*(NitroSwan-[\w.-]+)", workflow) != [
            f"NitroSwan-{CURRENT_VERSION}"]:
        errors.append("build.yaml: archive artifact name mismatch")
    return errors


def validate(root: Path, records: list[tuple[str, str]]) -> list[str]:
    errors = []
    names = {name for _, name in records}
    texts = {}
    folded = {}
    for mode, name in records:
        previous = folded.setdefault(name.casefold(), name)
        if previous != name:
            errors.append(f"case collision: {previous} / {name}")
        if mode == "160000":
            continue
        path = root / name
        if mode == "120000":
            errors.append(f"{name}: symlink requires manual portability review")
            continue
        if not path.is_file():
            errors.append(f"{name}: tracked file missing")
            continue
        suffix = PurePosixPath(name).suffix.lower()
        if (suffix in PRIVATE_SUFFIXES or
                name.startswith((".local-test-assets/", "local-reports/"))):
            errors.append(f"{name}: private test input/output must not be tracked")
        if (suffix in BUILD_SUFFIXES or
                any(part in {"build", "__pycache__"} for part in path.relative_to(root).parts)
                or PurePosixPath(name).name == "compile_commands.json"):
            errors.append(f"{name}: generated build output must not be tracked")
        if suffix == ".bin" and name not in ALLOWED_BINARIES:
            errors.append(f"{name}: unreviewed binary asset (not a blanket bin ignore)")
        data = path.read_bytes()
        if mode == "100755" and not data.startswith(b"#!"):
            errors.append(f"{name}: executable bit on a non-script")
        if b"\0" in data:
            continue
        try:
            content = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            continue
        texts[name] = content
        errors.extend(check_text(name, content, names))
    for name in REQUIRED_DOCS:
        if name not in texts:
            errors.append(f"{name}: required tracked document missing")
    errors.extend(check_versions(texts))
    return errors


def main() -> int:
    try:
        records = tracked_files(ROOT)
        errors = validate(ROOT, records)
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or b"").decode("utf-8", errors="replace").strip()
        print(f"FAIL repository scan: {error}\n{detail}", file=sys.stderr)
        return 1
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"FAIL repository scan: {error}", file=sys.stderr)
        return 1
    for error in errors:
        print(f"FAIL {error}", file=sys.stderr)
    if errors:
        return 1
    print(f"PASS repository hygiene: {len(records)} tracked entries including submodules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
