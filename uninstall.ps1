# AWING Auto Login - Uninstaller
# Usage: irm https://raw.githubusercontent.com/dmsang/O-ENGLoin/v1.0.10/uninstall.ps1 | iex

$ErrorActionPreference = "SilentlyContinue"

Write-Host ""
Write-Host "  ================================" -ForegroundColor Cyan
Write-Host "   AWING Auto Login - Uninstaller " -ForegroundColor Cyan
Write-Host "  ================================" -ForegroundColor Cyan
Write-Host ""

$INST = "$env:LOCALAPPDATA\AWING-Login"

# 1. Kill any running instances
Write-Host "  [1/4] Stopping running instances..." -ForegroundColor Cyan
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*AWING-Login*" -or $_.CommandLine -like "*awing*" } | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Milliseconds 800

# 2. Remove desktop shortcuts and batch files
Write-Host "  [2/4] Removing desktop shortcuts and batch files..." -ForegroundColor Cyan

$desktopDirs = @(
    [Environment]::GetFolderPath('Desktop'),
    "$env:USERPROFILE\Desktop",
    "$env:USERPROFILE\OneDrive\Desktop",
    "$env:PUBLIC\Desktop",
    [Environment]::GetFolderPath('CommonDesktopDirectory')
) | Select-Object -Unique | Where-Object { $_ -and (Test-Path $_) }

$filePatterns = @(
    "AWING Auto Login.lnk",
    "AWING Auto Login.bat",
    "AWING-Login.lnk",
    "AWING-Login.bat",
    "wifi.lnk",
    "wifi.bat",
    "wifi.cmd"
)

$removedCount = 0
foreach ($dir in $desktopDirs) {
    foreach ($pat in $filePatterns) {
        $p = Join-Path $dir $pat
        if (Test-Path $p) {
            Remove-Item -Path $p -Force -ErrorAction SilentlyContinue
            Write-Host "        Removed: $p" -ForegroundColor Green
            $removedCount++
        }
    }
}
if ($removedCount -eq 0) {
    Write-Host "        No desktop shortcuts or batch files found." -ForegroundColor DarkGray
}

# 3. Remove 'wifi' command
Write-Host "  [3/4] Removing 'wifi' command..." -ForegroundColor Cyan
$waFiles = @(
    "$env:LOCALAPPDATA\Microsoft\WindowsApps\wifi.cmd",
    "$env:LOCALAPPDATA\Microsoft\WindowsApps\wifi.bat"
)
foreach ($wf in $waFiles) {
    if (Test-Path $wf) {
        Remove-Item -Path $wf -Force -ErrorAction SilentlyContinue
        Write-Host "        Command removed: $wf" -ForegroundColor Green
    }
}

# 4. Remove install directory
Write-Host "  [4/4] Removing app files..." -ForegroundColor Cyan
if (Test-Path $INST) {
    Remove-Item -Path $INST -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path $INST) {
        Start-Sleep -Seconds 1
        Remove-Item -Path $INST -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (-not (Test-Path $INST)) {
        Write-Host "        App directory removed." -ForegroundColor Green
    } else {
        Write-Host "        Note: Some files may be cleaned up on next reboot." -ForegroundColor Yellow
    }
} else {
    Write-Host "        App directory not found." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "  [OK] AWING Auto Login has been completely uninstalled." -ForegroundColor Green
Write-Host ""
