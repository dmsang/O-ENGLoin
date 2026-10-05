@echo off
echo Installing AWING Auto Login...
powershell -ExecutionPolicy Bypass -Command "if (Test-Path '%~dp0install.ps1') { & '%~dp0install.ps1' } else { irm https://raw.githubusercontent.com/dmsang/O-ENGLoin/v1.0.9/install.ps1 | iex }"
pause