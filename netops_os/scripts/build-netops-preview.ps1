[CmdletBinding()]
param(
    [switch]$Install,
    [string]$DiskImage = '',
    [switch]$UseWHPX
)

$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$osRoot = (Resolve-Path (Join-Path $scriptRoot '..')).Path
$vmRoot = 'C:\NetOpsVM'
$DebianVersion = '12.15.0'
$archiveRoot = "https://cdimage.debian.org/cdimage/archive/$DebianVersion/amd64/iso-cd"
$isoName = "debian-$DebianVersion-amd64-netinst.iso"
$iso = Join-Path $vmRoot $isoName
# Keep the default image stable, but allow a new preview to be built beside it.
$disk = if ($DiskImage) { [IO.Path]::GetFullPath($DiskImage) } else { Join-Path $vmRoot 'netops-os.qcow2' }
$kernel = Join-Path $vmRoot 'vmlinuz'
$initrd = Join-Path $vmRoot 'initrd.gz'
$payloadRoot = Join-Path $vmRoot 'payload'
$payload = Join-Path $vmRoot 'netops-payload.tar.gz'
$preseed = Join-Path $vmRoot 'preseed.cfg'
$sourceInstallerSplash = Join-Path $osRoot 'guest\netops-splash.bmp'
$installerSplash = Join-Path $vmRoot 'netops-installer-splash.bmp'
$qemu = 'C:\Program Files\qemu\qemu-system-x86_64.exe'
$qemuImg = 'C:\Program Files\qemu\qemu-img.exe'

New-Item -ItemType Directory -Force -Path $vmRoot | Out-Null
if (-not (Test-Path $qemu)) { throw 'QEMU bulunamadi.' }
if (Test-Path -LiteralPath $sourceInstallerSplash) {
    Copy-Item -LiteralPath $sourceInstallerSplash -Destination $installerSplash -Force
}

if (-not (Test-Path $iso)) {
    Write-Host 'NetOps OS kurulum imaji indiriliyor...'
    Invoke-WebRequest -Uri "$archiveRoot/$isoName" -OutFile $iso
}

$checksumUrls = @(
    "$archiveRoot/SHA512SUMS",
    "https://ftp.de.debian.org/debian-cd/cdimage/archive/$DebianVersion/amd64/iso-cd/SHA512SUMS"
)
$line = $null
foreach ($checksumUrl in $checksumUrls) {
    try {
        $shaText = (Invoke-WebRequest -Uri $checksumUrl -UseBasicParsing -TimeoutSec 45).Content
        $line = ($shaText -split "`n" | Where-Object { $_ -match [regex]::Escape($isoName) } | Select-Object -First 1)
        if ($line) { break }
    } catch { }
}
if ($line) {
    $expected = ($line -split '\s+')[0].ToUpperInvariant()
    $actual = (Get-FileHash -LiteralPath $iso -Algorithm SHA512).Hash.ToUpperInvariant()
    if ($expected -ne $actual) { throw 'Kurulum ISO SHA512 dogrulamasi basarisiz.' }
    Write-Host 'Kurulum ISO SHA512 dogrulandi.'
} elseif ((Get-Item -LiteralPath $iso).Length -lt 500MB) {
    throw 'Kurulum ISO checksum alinamadi ve dosya boyutu beklenen resmi boyutla eslesmiyor.'
} else {
    Write-Warning 'Checksum sunucusu yanit vermedi; resmi boyut kontrolu gecildi.'
}

if (-not (Test-Path $disk)) { & $qemuImg create -f qcow2 $disk 8G | Out-Null }

# Always refresh these files: reusing a different release's initrd causes
# installer component and kernel-module mismatches.
$mounted = Mount-DiskImage -ImagePath $iso -PassThru
try {
    $volume = $mounted | Get-Volume
    $drive = "$($volume.DriveLetter):"
    Copy-Item -LiteralPath (Join-Path $drive 'install.amd\vmlinuz') -Destination $kernel -Force
    Copy-Item -LiteralPath (Join-Path $drive 'install.amd\initrd.gz') -Destination $initrd -Force
} finally {
    Dismount-DiskImage -ImagePath $iso
}

Remove-Item -LiteralPath $payloadRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $payloadRoot | Out-Null
Copy-Item -Path (Join-Path $osRoot 'guest\*') -Destination $payloadRoot -Recurse -Force
if (Test-Path $payload) { Remove-Item -LiteralPath $payload -Force }
tar -czf $payload -C $payloadRoot .

# This preview runs locally inside QEMU; keep the demo login easy to remember.
$password = '1234'
$hash = (& 'C:\msys64\ucrt64\bin\openssl.exe' passwd -6 $password).Trim()
$template = Get-Content -LiteralPath (Join-Path $osRoot 'seed\preseed.cfg.template') -Raw
$template.Replace('__NETOPS_PASSWORD_HASH__', $hash) | Set-Content -LiteralPath $preseed -Encoding ASCII
Set-Content -LiteralPath (Join-Path $vmRoot 'netops-preview-credentials.txt') -Value "User: netops`r`nPassword: $password`r`n" -Encoding ASCII

Write-Host "NetOps OS hazirlik dosyalari: $vmRoot"
Write-Host 'ISO ve payload hazir. Kurulum icin -Install parametresi kullan.'
if (-not $Install) { exit 0 }

$server = Start-Process -FilePath 'python.exe' -ArgumentList @('-m','http.server','8000','--bind','0.0.0.0','--directory',$vmRoot) -PassThru -WindowStyle Hidden
try {
    $accel = if ($UseWHPX) { 'whpx,kernel-irqchip=off' } else { 'tcg' }
    $bootConfig = 'menu=off'
    if (Test-Path -LiteralPath $installerSplash) {
        $bootConfig = "menu=off,splash=$([IO.Path]::GetFullPath($installerSplash)),splash-time=2500"
    }
    $argsList = @(
        '-machine','q35','-accel',$accel,'-m','4096','-smp','4',
        '-boot',$bootConfig,
        '-drive',"file=$disk,format=qcow2,if=virtio",
        '-cdrom',$iso,
        '-kernel',$kernel,
        '-initrd',$initrd,
        '-append','auto=true priority=critical preseed/url=http://10.0.2.2:8000/preseed.cfg ---',
        '-netdev','user,id=net0',
        '-device','e1000,netdev=net0',
        '-no-reboot'
    )
    Write-Host "NetOps OS kurulumu QEMU icinde basliyor... Hizlandirma: $accel"
    & $qemu @argsList
} finally {
    Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
}
