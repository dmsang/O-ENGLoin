# AWING Auto Login - Uninstaller
# Usage: irm https://raw.githubusercontent.com/dmsang/O-ENGLoin/master/uninstall.ps1 | iex

$ErrorActionPreference = "SilentlyContinue"

Write-Host ""
Write-Host "  ================================" -ForegroundColor Cyan
Write-Host "   AWING Auto Login - Uninstaller " -ForegroundColor Cyan
Write-Host "  ================================" -ForegroundColor Cyan
Write-Host ""

$INST = "$env:LOCALAPPDATA\AWING-Login"
$DESKTOP = [Environment]::GetFolderPath('Desktop')
$SHORTCUT = "$DESKTOP\AWING Auto Login.lnk"
$WIFI_CMD = "$env:LOCALAPPDATA\Microsoft\WindowsApps\wifi.cmd"

# 1. Kill any running instances
Write-Host "  [1/4] Stopping running instances..." -ForegroundColor Cyan
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*AWING-Login*" } | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Milliseconds 500

# 2. Remove desktop shortcut
Write-Host "  [2/4] Removing desktop shortcut..." -ForegroundColor Cyan
if (Test-Path $SHORTCUT) {
    Remove-Item -Path $SHORTCUT -Force
    Write-Host "        Shortcut removed." -ForegroundColor Green
} else {
    Write-Host "        No shortcut found." -ForegroundColor DarkGray
}

# 3. Remove 'wifi' command
Write-Host "  [3/4] Removing 'wifi' command..." -ForegroundColor Cyan
if (Test-Path $WIFI_CMD) {
    Remove-Item -Path $WIFI_CMD -Force
    Write-Host "        'wifi' command removed." -ForegroundColor Green
} else {
    Write-Host "        'wifi' command not found." -ForegroundColor DarkGray
}

# 4. Remove install directory
Write-Host "  [4/4] Removing app files..." -ForegroundColor Cyan
if (Test-Path $INST) {
    Remove-Item -Path $INST -Recurse -Force
    Write-Host "        App directory removed." -ForegroundColor Green
} else {
    Write-Host "        App directory not found." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "  [OK] AWING Auto Login has been completely uninstalled." -ForegroundColor Green
Write-Host ""
