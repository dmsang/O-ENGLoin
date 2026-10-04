#!/usr/bin/env bash
# AWING Auto Login — Linux Uninstaller
# Run with: curl -sSL https://raw.githubusercontent.com/dmsang/O-ENGLoin/master/uninstall.sh | bash

set -e

INSTALL_DIR="$HOME/.local/share/awing-login"
BIN_DIR="$HOME/.local/bin"

echo ""
echo -e "\033[1;33mUninstalling AWING Auto Login...\033[0m"

# 1. wifi command
if [ -f "$BIN_DIR/wifi" ]; then
    rm -f "$BIN_DIR/wifi"
    echo -e "\033[1;32m  ✓ 'wifi' launcher removed.\033[0m"
fi

# 2. Desktop entry
if [ -f "$HOME/.local/share/applications/awing-login.desktop" ]; then
    rm -f "$HOME/.local/share/applications/awing-login.desktop"
    echo -e "\033[1;32m  ✓ Desktop entry removed.\033[0m"
fi

# 3. App files
if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
    echo -e "\033[1;32m  ✓ App files removed.\033[0m"
fi

echo -e "\033[1;32m\n✓ AWING Auto Login has been uninstalled successfully.\n\033[0m"