$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot
$env:GIT_CEILING_DIRECTORIES = Split-Path -Parent $ProjectRoot

$AiderBin = Join-Path $env:USERPROFILE ".local\bin"
if (Test-Path -LiteralPath $AiderBin) {
    $env:PATH = "$AiderBin;$env:PATH"
}

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    throw "Ollama bulunamadı. Ollama kurulumu gerekli."
}

$env:OLLAMA_API_BASE = "http://127.0.0.1:11434"
$Model = "ollama/qwen2.5-coder:7b"

Write-Host "NetOps Aider başlıyor: yerel Ollama" -ForegroundColor Green
Write-Host "Model: $Model" -ForegroundColor DarkGray
Write-Host "API anahtarı ve kullanım kotası yok; hız bilgisayarına bağlıdır." -ForegroundColor DarkGray

$health = $null
try { $health = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing -TimeoutSec 2 } catch {}
if (-not $health) {
    Start-Process -FilePath (Get-Command ollama).Source -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 2
}

& aider --config ".aider.conf.yml" --model $Model

