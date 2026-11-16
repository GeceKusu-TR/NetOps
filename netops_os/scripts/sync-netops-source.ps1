[CmdletBinding()]
param(
    [string]$ProjectRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)),
    [string]$PayloadRoot = 'C:\NetOpsVM\payload\netops-app'
)

$ErrorActionPreference = 'Stop'
$extensions = @('.py', '.json', '.nops', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.mp3', '.wav', '.ttf', '.otf')
$files = Get-ChildItem -LiteralPath $ProjectRoot -File | Where-Object { $extensions -contains $_.Extension.ToLowerInvariant() }
$files += Get-Item -LiteralPath (Join-Path $ProjectRoot 'requirements_live.txt')

New-Item -ItemType Directory -Force -Path $PayloadRoot | Out-Null
foreach ($file in $files) {
    Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $PayloadRoot $file.Name) -Force
}

Write-Host "NetOps kaynak paketi hazir: $PayloadRoot"
Write-Host "Dosya sayisi: $($files.Count)"
