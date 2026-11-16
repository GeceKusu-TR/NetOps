[CmdletBinding()]
param(
    [string]$DiskImage = '',
    [string]$IsoImage = '',
    [ValidateRange(512, 4096)]
    [int]$MemoryMB = 1024,
    [ValidateRange(1, 4)]
    [int]$Cpus = 2,
    [switch]$Snapshot,
    [switch]$NoSnapshot,
    [switch]$NoGui,
    [switch]$ShowQemuChrome,
    [switch]$UseWHPX,
    [ValidateRange(1024, 65535)]
    [int]$RemotePort = 9876,
    [switch]$NoRemotePortForward
)

$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $DiskImage) {
    $legacyDisk = 'C:\NetOpsVM\netops-os-xfce-remote.qcow2'
    $asciiDisk = 'C:\NetOpsVM\netops-os.qcow2'
    $bootDisk = 'C:\NetOpsVM\netops-os-boot.vhdx'
    $projectDisk = Join-Path $scriptRoot '..\artifacts\netops-os.qcow2'
    $DiskImage = if (Test-Path -LiteralPath $legacyDisk) {
        $legacyDisk
    } elseif (Test-Path -LiteralPath $bootDisk) {
        $bootDisk
    } elseif (Test-Path -LiteralPath $asciiDisk) {
        $asciiDisk
    } else {
        $projectDisk
    }
}
$qemu = Get-Command 'qemu-system-x86_64' -ErrorAction SilentlyContinue
if (-not $qemu) {
    $configured = $env:NETOPS_QEMU
    if ($configured -and (Test-Path -LiteralPath $configured)) {
        $qemu = Get-Item -LiteralPath $configured
    }
}
if (-not $qemu) {
    foreach ($candidate in @(
        'C:\Program Files\qemu\qemu-system-x86_64.exe',
        'C:\Program Files\QEMU\qemu-system-x86_64.exe'
    )) {
        if (Test-Path -LiteralPath $candidate) {
            $qemu = Get-Item -LiteralPath $candidate
            break
        }
    }
}
if (-not $qemu) {
    throw 'QEMU bulunamadi. QEMU kurulduktan sonra bu scripti yeniden calistir.'
}

$accel = if ($UseWHPX) { 'whpx,kernel-irqchip=off' } else { 'tcg' }
$argsList = @('-machine', 'q35', '-accel', $accel, '-m', "$MemoryMB", '-smp', "$Cpus")
$asciiSplash = 'C:\NetOpsVM\netops-splash.bmp'
$projectSplash = Join-Path $scriptRoot '..\guest\netops-splash.bmp'
$splashImage = if (Test-Path -LiteralPath $asciiSplash) { $asciiSplash } else { $projectSplash }
if (Test-Path -LiteralPath $splashImage) {
    # Show the NetOps artwork during firmware hand-off instead of a blank
    # SeaBIOS/terminal phase. The guest still owns its own quiet Plymouth boot.
    $argsList += @('-boot', "menu=off,splash=$([IO.Path]::GetFullPath($splashImage)),splash-time=5000")
}
$nic = if ($NoRemotePortForward) {
    'user,model=virtio'
} else {
    "user,model=virtio,hostfwd=tcp::${RemotePort}-:8765"
}
$display = 'sdl'
$argsList += @('-display', $display, '-nic', $nic)
if ($DiskImage -and (Test-Path -LiteralPath $DiskImage)) {
    $diskFormat = if ([IO.Path]::GetExtension($DiskImage).ToLowerInvariant() -eq '.vhdx') { 'vhdx' } else { 'qcow2' }
    $argsList += @('-drive', "file=$([IO.Path]::GetFullPath($DiskImage)),format=$diskFormat,if=virtio")
}
if ($IsoImage) {
    if (-not (Test-Path -LiteralPath $IsoImage)) { throw "ISO bulunamadi: $IsoImage" }
    $argsList += @('-cdrom', [IO.Path]::GetFullPath($IsoImage), '-boot', 'd')
}
if ($Snapshot -or -not $NoSnapshot) { $argsList += '-snapshot' }
if ($NoGui) { $argsList += '-nographic' }

if (-not $NoRemotePortForward) {
    Write-Host "NetOps OS uzak cihaz portu: host $RemotePort -> guest 8765"
}
Write-Host "NetOps OS QEMU baslatiliyor. Host Windows degistirilmiyor."
$qemuPath = if ($qemu.PSObject.Properties.Name -contains 'Source' -and $qemu.Source) {
    $qemu.Source
} else {
    $qemu.FullName
}

if ($NoGui -or $ShowQemuChrome) {
    & $qemuPath @argsList
    exit $LASTEXITCODE
}

# SDL is the stable backend for this legacy guest. Remove only the host window
# chrome after launch so the guest remains visible without a QEMU frame/taskbar.
if (-not ('NetOpsSurfaceWindow' -as [type])) {
    Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class NetOpsSurfaceWindow
{
    private const int GWL_STYLE = -16;
    private const long WS_CAPTION = 0x00C00000L;
    private const long WS_THICKFRAME = 0x00040000L;
    private const long WS_MINIMIZEBOX = 0x00020000L;
    private const long WS_MAXIMIZEBOX = 0x00010000L;
    private const long WS_SYSMENU = 0x00080000L;
    private const uint SWP_FRAMECHANGED = 0x0020;
    private const uint SWP_SHOWWINDOW = 0x0040;

    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtrW", SetLastError = true)]
    private static extern IntPtr GetWindowLongPtr(IntPtr hWnd, int nIndex);

    [DllImport("user32.dll", EntryPoint = "SetWindowLongPtrW", SetLastError = true)]
    private static extern IntPtr SetWindowLongPtr(IntPtr hWnd, int nIndex, IntPtr value);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool SetWindowPos(
        IntPtr hWnd, IntPtr hWndInsertAfter, int x, int y, int cx, int cy, uint flags);

    [DllImport("user32.dll")]
    private static extern int GetSystemMetrics(int index);

    public static void Apply(IntPtr hWnd)
    {
        long style = GetWindowLongPtr(hWnd, GWL_STYLE).ToInt64();
        long border = WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU;
        SetWindowLongPtr(hWnd, GWL_STYLE, new IntPtr(style & ~border));
        SetWindowPos(
            hWnd,
            new IntPtr(-1),
            0,
            0,
            GetSystemMetrics(0),
            GetSystemMetrics(1),
            SWP_FRAMECHANGED | SWP_SHOWWINDOW);
    }
}
"@
}

function Set-NetOpsSurfaceFullscreen {
    param([System.Diagnostics.Process]$Process)

    if ($Process.MainWindowHandle -ne [IntPtr]::Zero) {
        [NetOpsSurfaceWindow]::Apply($Process.MainWindowHandle)
        return $true
    }
    return $false
}

$qemuProcess = Start-Process -FilePath $qemuPath -ArgumentList $argsList -PassThru -WindowStyle Normal
for ($attempt = 0; $attempt -lt 80; $attempt++) {
    if ($qemuProcess.HasExited) { break }
    $qemuProcess.Refresh()
    if ($qemuProcess.MainWindowHandle -ne [IntPtr]::Zero) {
        Set-NetOpsSurfaceFullscreen -Process $qemuProcess
        break
    }
    Start-Sleep -Milliseconds 100
}
$qemuProcess.WaitForExit()
exit $qemuProcess.ExitCode
