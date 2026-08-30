param(
    [string]$Nasm = "nasm",
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$testDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$output = Join-Path $testDir "rom_fetch_waitstate.ws"

& $Python (Join-Path $testDir "generate_font.py")
if ($LASTEXITCODE -ne 0) { throw "font generation failed" }

Push-Location $testDir
try {
    & $Nasm -f bin -Wall -w-reloc-abs-word -o $output "rom_fetch_waitstate.asm"
    if ($LASTEXITCODE -ne 0) { throw "NASM build failed" }
} finally {
    Pop-Location
}

& $Python (Join-Path $testDir "fix_checksum.py") $output
if ($LASTEXITCODE -ne 0) { throw "checksum patch failed" }

Get-Item -LiteralPath $output | Select-Object FullName,Length
Get-FileHash -LiteralPath $output -Algorithm SHA256
