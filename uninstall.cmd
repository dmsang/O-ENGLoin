@echo off
echo Uninstalling AWING Auto Login...
powershell -ExecutionPolicy Bypass -Command "if (Test-Path '%~dp0uninstall.ps1') { & '%~dp0uninstall.ps1' } else { irm https://raw.githubusercontent.com/dmsang/O-ENGLoin/v1.0.9/uninstall.ps1 | iex }"
pause