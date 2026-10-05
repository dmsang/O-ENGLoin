# AWING Auto Login - Installer
# irm https://raw.githubusercontent.com/dmsang/O-ENGLoin/v1.0.9/install.ps1 | iex

$ErrorActionPreference = "Stop"
$REPO = "dmsang/O-ENGLoin"
$RAW  = "https://raw.githubusercontent.com/$REPO/v1.0.9"
$INST = "$env:LOCALAPPDATA\AWING-Login"

Write-Host ""
Write-Host "  ================================" -ForegroundColor Cyan
Write-Host "   AWING Auto Login - Installer  " -ForegroundColor Cyan
Write-Host "  ================================" -ForegroundColor Cyan
Write-Host ""

# 1. Python
$pyOK  = $false
$pyExe = "python"
try {
    $ver = (& python --version 2>&1) -replace "Python ", ""
    $ver = $ver.Trim()
    $pv  = $ver.Split(".")
    if ([int]$pv[0] -ge 3 -and [int]$pv[1] -ge 10) { $pyOK = $true }
} catch {}
if (-not $pyOK) {
    try {
        $v2 = (& py --version 2>&1) -replace "Python ", ""
        $p2 = $v2.Trim().Split(".")
        if ([int]$p2[0] -ge 3 -and [int]$p2[1] -ge 10) { $pyOK = $true; $pyExe = "py" }
    } catch {}
}
if (-not $pyOK) {
    Write-Host "  [1/5] Downloading Python 3.12..." -ForegroundColor Yellow
    $u = "https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
    $t = "$env:TEMP\py.exe"
    Invoke-WebRequest -Uri $u -OutFile $t -UseBasicParsing
    Start-Process $t -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1" -Wait -WindowStyle Hidden
    Remove-Item $t -Force -ErrorAction SilentlyContinue
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    Write-Host "        Python installed." -ForegroundColor Green
} else {
    Write-Host "  [1/5] Python OK ($ver)" -ForegroundColor Green
}

# 2. Download app files
Write-Host "  [2/5] Downloading app..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path "$INST\awing\screens" | Out-Null

$FILES = @(
    "main.py",
    "VERSION",
    "uninstall.ps1",
    "uninstall.cmd",
    "awing/__init__.py",
    "awing/compat.py",
    "awing/ui.py",
    "awing/settings.py",
    "awing/state.py",
    "awing/wifi.py",
    "awing/network.py",
    "awing/tray.py",
    "awing/screens/__init__.py",
    "awing/screens/wifi_popup.py",
    "awing/screens/auto_login.py",
    "awing/screens/nettest.py",
    "awing/screens/update.py",
    "awing/screens/help.py",
    "awing/screens/donate.py",
    "awing/beta.py",
    "awing/screens/beta_screen.py",
    "awing/screens/uninstall.py",
    "awing/screens/menu.py",
    "awing/screens/settings_screen.py"
)

foreach ($f in $FILES) {
    $target = Join-Path $INST ($f -replace '/', '\')
    $dir = Split-Path $target -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    $url = "$RAW/$f"
    Invoke-WebRequest -Uri $url -OutFile $target -UseBasicParsing
}
Write-Host "        Done." -ForegroundColor Green

# 3. Deps
Write-Host "  [3/5] Installing dependencies..." -ForegroundColor Cyan
& $pyExe -m pip install --quiet --upgrade pip
& $pyExe -m pip install --quiet requests beautifulsoup4 blessed pystray pillow speedtest-cli
Write-Host "        Done." -ForegroundColor Green

# 4. Desktop shortcut
Write-Host "  [4/5] Creating desktop shortcut..." -ForegroundColor Cyan
$lau = "$INST\AWING-Login.bat"
Set-Content -Path $lau -Encoding ASCII -Value ("@echo off`r`n`"$pyExe`" `"$INST\main.py`" %*")
$ws  = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut("$([Environment]::GetFolderPath('Desktop'))\AWING Auto Login.lnk")
$lnk.TargetPath       = $lau
$lnk.WorkingDirectory = $INST
$lnk.Description      = "AWING Auto Login"
$lnk.Save()
Write-Host "        Done." -ForegroundColor Green

# 5. Register 'wifi' command
Write-Host "  [5/5] Registering 'wifi' command..." -ForegroundColor Cyan
$wa = "$env:LOCALAPPDATA\Microsoft\WindowsApps"
$wf = "$wa\wifi.cmd"
New-Item -ItemType Directory -Force -Path $wa | Out-Null
Set-Content -Path $wf -Encoding ASCII -Value ("@echo off`r`n`"$pyExe`" `"$INST\main.py`" %*")
Write-Host "        Done. Now type 'wifi' in any terminal!" -ForegroundColor Green

Write-Host ""
Write-Host "  Installation complete!" -ForegroundColor Green
Write-Host "  - Desktop shortcut: AWING Auto Login" -ForegroundColor White
Write-Host "  - From any terminal: wifi" -ForegroundColor White
Write-Host "  - To uninstall: wifi --uninstall" -ForegroundColor DarkGray
Write-Host ""