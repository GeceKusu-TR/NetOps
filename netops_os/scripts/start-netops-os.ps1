[CmdletBinding()]
param(
    [int]$SplashSeconds = 35
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$qemu = 'C:\Program Files\qemu\qemu-system-x86_64.exe'
$disk = 'C:\NetOpsVM\netops-os-boot.vhdx'
$splash = 'C:\NetOpsVM\netops-splash.png'
$remotePort = 9876
if (-not (Test-Path -LiteralPath $qemu)) { throw "QEMU bulunamadi: $qemu" }
if (-not (Test-Path -LiteralPath $disk)) { throw "NetOps OS imaji bulunamadi: $disk" }
if (-not (Test-Path -LiteralPath $splash)) {
    $splash = Join-Path $PSScriptRoot '..\guest\netops-splash.png'
}

$qemuArgs = @(
    '-machine', 'q35',
    '-accel', 'tcg',
    '-m', '1024',
    '-smp', '2',
    '-drive', "file=$disk,format=vhdx,if=virtio",
    '-nic', "user,model=e1000,hostfwd=tcp::${remotePort}-:8765",
    '-display', 'sdl',
    '-snapshot',
    '-no-reboot',
    '-no-shutdown'
)
$qemuProcess = Start-Process -FilePath $qemu -ArgumentList $qemuArgs -PassThru

$form = New-Object System.Windows.Forms.Form
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::None
$form.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen
$form.ClientSize = New-Object System.Drawing.Size(640, 640)
$form.BackColor = [System.Drawing.Color]::Black
$form.TopMost = $true
$form.ShowInTaskbar = $false

$picture = New-Object System.Windows.Forms.PictureBox
$picture.Dock = [System.Windows.Forms.DockStyle]::Fill
$picture.SizeMode = [System.Windows.Forms.PictureBoxSizeMode]::Zoom
$picture.BackColor = [System.Drawing.Color]::Black
$picture.Image = [System.Drawing.Image]::FromFile((Resolve-Path -LiteralPath $splash).Path)
$form.Controls.Add($picture)

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = [Math]::Max(3, $SplashSeconds) * 1000
$timer.Add_Tick({
    $timer.Stop()
    $form.Close()
})
$form.Add_Shown({ $timer.Start() })
[System.Windows.Forms.Application]::Run($form)
$picture.Image.Dispose()
$timer.Dispose()
$form.Dispose()
