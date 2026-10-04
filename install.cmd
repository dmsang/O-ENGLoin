@echo off
echo Installing AWING Auto Login...
powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/dmsang/O-ENGLoin/v1.0.7/install.ps1 | iex"
pause