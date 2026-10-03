# AWING Auto Login

Auto-login for AWING captive portal WiFi. Terminal UI + system tray.

## One-line Install

**PowerShell**:
```powershell
irm https://raw.githubusercontent.com/dmsang/O-ENGLoin/master/install.ps1 | iex
```

**Command Prompt**:
```cmd
powershell -ExecutionPolicy Bypass -c "irm 'https://raw.githubusercontent.com/dmsang/O-ENGLoin/master/install.ps1' | iex"
```

Or download and double-click **install.cmd**.

## Manual Install

1. Python 3.10+ from https://python.org
2. `pip install requests beautifulsoup4 blessed pystray pillow speedtest-cli`
3. `python app2.py`

## Features

- Auto-reconnects when captive portal expires
- System tray background mode
- Network speed test
- Auto-update via GitHub Releases
- Configurable SSID filter, notifications

## Update

Select **Check for Updates** in the main menu, or re-run the installer.

## Requirements

Windows 10/11, Python 3.10+

## License

MIT
