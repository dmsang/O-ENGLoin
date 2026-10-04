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

**Linux (Ubuntu, Debian, Fedora, Arch, etc.)**:
```bash
curl -sSL https://raw.githubusercontent.com/dmsang/O-ENGLoin/master/install.sh | bash
```

## Manual Install

1. Python 3.10+ from https://python.org
2. `pip install requests beautifulsoup4 blessed pystray pillow speedtest-cli`
3. `python main.py`

## Features

- Auto-reconnects when captive portal expires
- System tray background mode
- Network speed test
- Auto-update via GitHub Releases
- Configurable SSID filter, notifications

## Update

Select **Check for Updates** in the main menu, or re-run the installer.

## Requirements

Windows 10/11, Linux (Ubuntu, Fedora, Arch, etc.), Python 3.10+

## License

MIT

## Uninstall

- From app: select 'Uninstall' from menu, or run 'wifi --uninstall'
- One-line PowerShell: irm https://raw.githubusercontent.com/dmsang/O-ENGLoin/master/uninstall.ps1 | iex
- Command Prompt: download and run install.cmd or uninstall.cmd
- Linux (one-line): curl -sSL https://raw.githubusercontent.com/dmsang/O-ENGLoin/master/uninstall.sh | bash
