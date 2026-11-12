# Restore the embedded firmware resources of the NetUpdaterClone updater.
#
# The decompiled source tree in
#   07_open_source_tools/netupdaterclone_src/
# ships without the embedded .DigBin blobs (18 MB) to keep the archive small.
# They are reproduced from the shipped updater executable:
#
#   02_source_binaries/Digitech.RP.Series.Firmware.Updater.exe
#
# The executable is a .NET single-file bundle; the application assembly sits
# at file offset 0x52000 and carries the resources as manifest resources.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File extract_updater_resources.ps1
#   powershell -ExecutionPolicy Bypass -File extract_updater_resources.ps1 `
#              -Exe ..\02_source_binaries\Digitech.RP.Series.Firmware.Updater.exe `
#              -Out ..\07_open_source_tools\netupdaterclone_src
#
# Requires Mono.Cecil (archived in 07_open_source_tools/ilspycmd/Mono.Cecil.dll).

param(
    [string]$Exe  = "$PSScriptRoot\..\02_source_binaries\Digitech.RP.Series.Firmware.Updater.exe",
    [string]$Out  = "$PSScriptRoot\..\07_open_source_tools\netupdaterclone_src",
    [int]   $AppOffset = 0x52000
)

$ErrorActionPreference = "Stop"

$cecil = Join-Path $PSScriptRoot "..\07_open_source_tools\ilspycmd\Mono.Cecil.dll"
if (-not (Test-Path $cecil)) { throw "Mono.Cecil not found: $cecil" }
Add-Type -Path (Resolve-Path $cecil)

$bytes = [IO.File]::ReadAllBytes($Exe)
$app = Join-Path $env:TEMP ("updater_app_{0}.dll" -f [Guid]::NewGuid().ToString("N").Substring(0,8))
[IO.File]::WriteAllBytes($app, $bytes[$AppOffset..($bytes.Length - 1)])

try {
    $asm = [Mono.Cecil.AssemblyDefinition]::ReadAssembly($app)
    $n = 0
    foreach ($res in $asm.MainModule.Resources) {
        if ($res.ResourceType -ne "Embedded") { continue }
        $name = $res.Name
        $path = Join-Path $Out $name
        $dir = Split-Path $path
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
        $ms = New-Object IO.MemoryStream
        $s = $res.GetResourceStream()
        $s.CopyTo($ms)
        [IO.File]::WriteAllBytes($path, $ms.ToArray())
        $sha = [BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash($ms.ToArray())).Replace('-','').ToLower()
        "{0,-58} {1,9} bytes  {2}" -f $name, $ms.Length, $sha.Substring(0,16)
        $n++
    }
    "extracted $n embedded resources into $Out"
}
finally {
    Remove-Item $app -ErrorAction SilentlyContinue
}
