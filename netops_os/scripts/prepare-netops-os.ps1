[CmdletBinding()]
param(
    [string]$OutputDirectory = ''
)

$ErrorActionPreference = 'Stop'
if (-not $OutputDirectory) {
    $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    $OutputDirectory = Join-Path $scriptRoot '..\artifacts'
}
$output = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $output | Out-Null

$qemuCommand = Get-Command 'qemu-system-x86_64' -ErrorAction SilentlyContinue
if (-not $qemuCommand) {
    foreach ($candidate in @('C:\Program Files\qemu\qemu-system-x86_64.exe', 'C:\Program Files\QEMU\qemu-system-x86_64.exe')) {
        if (Test-Path -LiteralPath $candidate) { $qemuCommand = Get-Item -LiteralPath $candidate; break }
    }
}
$checks = [ordered]@{ QEMU = [bool]$qemuCommand }
$checks | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output 'host-capabilities.json') -Encoding UTF8

Write-Host 'NetOps OS preview hazirlik kontrolu tamamlandi.'
$checks.GetEnumerator() | ForEach-Object { Write-Host ("{0}: {1}" -f $_.Key, $_.Value) }
if (-not $checks.QEMU) {
    Write-Warning 'QEMU kurulu degil. ISO/virtual disk calistirma adimi beklemede.'
}
