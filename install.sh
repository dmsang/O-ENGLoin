#!/usr/bin/env bash
# AWING Auto Login — Linux Installer (Ubuntu, Debian, Fedora, Arch, etc.)
# Run with: curl -sSL https://raw.githubusercontent.com/dmsang/O-ENGLoin/master/install.sh | bash

set -e

REPO="dmsang/O-ENGLoin"
RAW="https://raw.githubusercontent.com/$REPO/master"
INSTALL_DIR="$HOME/.local/share/awing-login"
BIN_DIR="$HOME/.local/bin"

echo ""
echo -e "\033[1;36m  ================================\033[0m"
echo -e "\033[1;36m   AWING Auto Login - Installer   \033[0m"
echo -e "\033[1;36m  ================================\033[0m"
echo ""

# 1. Python 3.10+ check / install
echo -e "\033[1;33m  [1/4] Checking Python...\033[0m"
PY=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        VER=$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)
        MAJOR=$(echo "$VER" | cut -d. -f1)
        MINOR=$(echo "$VER" | cut -d. -f2)
        if [ "${MAJOR:-0}" -ge 3 ] && [ "${MINOR:-0}" -ge 10 ]; then
            PY="$candidate"
            break
        fi
    fi
done

if [ -z "$PY" ]; then
    echo "        Installing Python 3..."
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update -qq && sudo apt-get install -y -qq python3 python3-pip python3-venv
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y python3 python3-pip
    elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -Sy --noconfirm python python-pip
    else
        echo -e "\033[1;31mError: Python 3.10+ not found and no supported package manager detected.\033[0m"
        exit 1
    fi
    PY="python3"
fi
echo -e "\033[1;32m        Python OK ($($PY --version))\033[0m"

# 2. Download app files
echo -e "\033[1;33m  [2/4] Downloading app...\033[0m"
mkdir -p "$INSTALL_DIR/awing/screens" "$BIN_DIR"

FILES=(
    "main.py"
    "VERSION"
    "awing/__init__.py"
    "awing/compat.py"
    "awing/ui.py"
    "awing/settings.py"
    "awing/state.py"
    "awing/wifi.py"
    "awing/network.py"
    "awing/tray.py"
    "awing/screens/__init__.py"
    "awing/screens/wifi_popup.py"
    "awing/screens/auto_login.py"
    "awing/screens/nettest.py"
    "awing/screens/update.py"
    "awing/screens/help.py"
    "awing/screens/uninstall.py"
    "awing/screens/menu.py"
    "awing/screens/settings_screen.py"
)

for file in "${FILES[@]}"; do
    TARGET="$INSTALL_DIR/$file"
    mkdir -p "$(dirname "$TARGET")"
    curl -sSL "$RAW/$file" -o "$TARGET"
done
echo -e "\033[1;32m        Done.\033[0m"

# 3. Dependencies
echo -e "\033[1;33m  [3/4] Installing dependencies...\033[0m"
# Install core terminal/network deps without pystray (avoids Gtk requirement on headless/minimal systems)
$PY -m pip install --quiet --upgrade pip 2>/dev/null || true
$PY -m pip install --quiet requests beautifulsoup4 blessed speedtest-cli 2>/dev/null || \
    $PY -m pip install --quiet --break-system-packages requests beautifulsoup4 blessed speedtest-cli 2>/dev/null || \
    pip install --quiet requests beautifulsoup4 blessed speedtest-cli 2>/dev/null
echo -e "\033[1;32m        Done.\033[0m"

# 4. Launcher script
echo -e "\033[1;33m  [4/4] Creating 'wifi' launcher...\033[0m"
cat > "$BIN_DIR/wifi" <<EOF
#!/usr/bin/env bash
exec "$PY" "$INSTALL_DIR/main.py" "\$@"
EOF
chmod +x "$BIN_DIR/wifi"

# Ensure ~/.local/bin is in PATH for future shells
SHELL_RC=""
if [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
elif [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -f "$HOME/.profile" ]; then
    SHELL_RC="$HOME/.profile"
fi

if [ -n "$SHELL_RC" ] && ! grep -q '\.local/bin' "$SHELL_RC" 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
fi

# Optional: desktop entry
DESK_DIR="$HOME/.local/share/applications"
if [ -d "$DESK_DIR" ] || [ -d "$HOME/.local/share" ]; then
    mkdir -p "$DESK_DIR"
    cat > "$DESK_DIR/awing-login.desktop" <<EOF
[Desktop Entry]
Name=AWING Auto Login
Comment=Keep internet alive on captive portal Wi-Fi
Exec=$BIN_DIR/wifi
Terminal=true
Type=Application
Categories=Network;Utility;
EOF
fi

echo -e "\033[1;32m        Done!\033[0m"
echo ""
echo -e "\033[1;32m  Installation complete!\033[0m"
echo -e "  - Run from anywhere: \033[1mwifi\033[0m"
echo -e "  - To uninstall:     \033[1mwifi --uninstall\033[0m"
echo ""

# Export PATH for current session if not yet present
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) echo -e "\033[2m  Note: Run 'source $SHELL_RC' or re-open terminal to use 'wifi'.\033[0m";;
esac