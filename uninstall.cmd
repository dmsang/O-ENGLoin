@echo off
echo Uninstalling AWING Auto Login...
powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/dmsang/O-ENGLoin/v1.0.7/uninstall.ps1 | iex"
pause