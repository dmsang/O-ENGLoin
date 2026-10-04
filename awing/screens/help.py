"""awing/screens/help.py — User guide / help screen."""
from awing import (term, bold, C_TITLE, C_BORDER, C_SEL, C_OK, C_ERR, C_WARN,
                   C_DIM, C_KEY, C_VAL, RST, render, center_in, box_top,
                   box_mid, box_bot, box_row, sep_row, read_key,
                   mouse_scroll_up, mouse_scroll_down, APP_VERSION)

def help_screen():
    scroll = [0]
    HELP_LINES = [
        C_TITLE + bold("=== AWING AUTO LOGIN - USER GUIDE ===") + RST,
        "",
        C_TITLE + bold("[1] WHAT IS THIS APP?") + RST,
        "  AWING Auto Login keeps your internet alive on captive portal",
        "  Wi-Fi networks (e.g. INET Free WiFi). It constantly checks",
        "  connectivity and automatically re-authenticates when the session expires.",
        "",
        C_TITLE + bold("[2] MAIN MENU OPTIONS") + RST,
        "  " + C_KEY + "▶  Auto Login" + RST + "        Live monitoring screen with real-time logs.",
        "  " + C_KEY + "□  Run in Background" + RST + " Minimizes console to system tray.",
        "  " + C_KEY + "⎔  Network Test" + RST + "      Speed test, target server, ping, LAN & WAN IP.",
        "  " + C_KEY + "⬆  Check for Updates" + RST + " Checks GitHub Releases for new versions.",
        "  " + C_KEY + "?  User Guide" + RST + "         This help screen.",
        "  " + C_KEY + "⚙  Settings" + RST + "           Configure gateway, intervals, debug, etc.",
        "  " + C_KEY + "✕  Exit" + RST + "               Quit the application.",
        "",
        C_TITLE + bold("[3] SYSTEM TRAY (BACKGROUND MODE)") + RST,
        "  • Select 'Run in Background' from the main menu.",
        "  • Console window hides; icon appears in taskbar (bottom-right).",
        "  • Tray icon color shows live status:",
        "      " + C_OK + "● Green" + RST + "  = Online (internet active)",
        "      " + C_ERR + "● Red" + RST + "    = Offline (disconnected)",
        "      " + C_WARN + "● Yellow" + RST + " = Logging in to captive portal",
        "  • Left-click or right-click icon -> 'Open window' to restore CLI.",
        "  • Right-click icon -> 'Exit' to quit completely.",
        "",
        C_TITLE + bold("[4] QUICK COMMAND ('wifi')") + RST,
        "  • Open the app from ANY terminal simply by typing:  " + C_OK + "wifi" + RST,
        "  • Works in CMD, PowerShell, Windows Terminal, and Win+R dialog.",
        "",
        C_TITLE + bold("[5] KEYBOARD SHORTCUTS") + RST,
        "  " + C_KEY + "↑ / ↓" + RST + "           Move selection / scroll logs & guide",
        "  " + C_KEY + "Enter" + RST + "           Select / Confirm / Toggle ON-OFF",
        "  " + C_KEY + "Space / ← →" + RST + "     Toggle ON/OFF on boolean settings directly",
        "  " + C_KEY + "End / Home" + RST + "      Jump to newest / oldest line in logs & guide",
        "  " + C_KEY + "Q / Esc" + RST + "         Back to previous screen / Exit",
        "  " + C_KEY + "X" + RST + "               Stop background worker while viewing logs",
        "",
        C_TITLE + bold("[6] SETTINGS EXPLAINED") + RST,
        "  • " + C_VAL + "Default Gateway" + RST + "      Router IP address (default: 192.168.200.1)",
        "  • " + C_VAL + "Check Interval" + RST + "       Seconds between connectivity checks (15s)",
        "  • " + C_VAL + "Retry Interval" + RST + "       Seconds before retrying after failure (5s)",
        "  • " + C_VAL + "Required WiFi SSID" + RST + "   Target Wi-Fi SSID ('INET - Free WiFi')",
        "  • " + C_VAL + "Notifications" + RST + "        Desktop notifications on status change",
        "  • " + C_VAL + "Debug Mode" + RST + "           Detailed logs (HTTP, tokens, MAC, etc.)",
        "",
        C_TITLE + bold("[7] ONE-LINE INSTALL COMMAND") + RST,
        "  " + C_DIM + "irm https://raw.githubusercontent.com/dmsang/O-ENGLoin/master/install.ps1 | iex" + RST,
    ]
    def build():
        W = term.width or 80; H = term.height or 24
        bw = min(74, W - 4); bh = H - 4; bx = (W - bw) // 2; by = 2
        content_h = bh - 4
        total = len(HELP_LINES)
        start = scroll[0]
        rows = [""] * H
        rows[by]   = " " * bx + box_top(bw, " USER GUIDE ")
        rows[by+1] = " " * bx + box_row(bw, center_in(C_TITLE + bold(" AWING Auto Login ") + C_DIM + "v" + APP_VERSION + RST, bw - 2))
        rows[by+2] = " " * bx + sep_row(bw)
        for i in range(content_h):
            idx = start + i
            line = HELP_LINES[idx] if idx < total else ""
            rows[by + 3 + i] = " " * bx + box_row(bw, " " + line)
        sep_y = by + 3 + content_h
        rows[sep_y] = " " * bx + sep_row(bw)
        pct = f"({start + 1}-{min(start + content_h, total)}/{total})"
        hint = C_KEY + "↑↓" + RST + " scroll " + C_DIM + pct + RST + "   " + C_KEY + "Home/End" + RST + " top/bottom   " + C_KEY + "Q/Esc" + RST + " back"
        rows[sep_y + 1] = " " * bx + box_row(bw, " " + hint)
        rows[sep_y + 2] = " " * bx + box_bot(bw)
        return rows

    while True:
        render(build())
        key = read_key()
        H = term.height or 24; content_h = H - 8; total = len(HELP_LINES)
        max_scroll = max(0, total - content_h)
        if key.code == term.KEY_UP or mouse_scroll_up(key):
            scroll[0] = max(0, scroll[0] - 1)
        elif key.code == term.KEY_DOWN or mouse_scroll_down(key):
            scroll[0] = min(max_scroll, scroll[0] + 1)
        elif key.code == term.KEY_HOME:
            scroll[0] = 0
        elif key.code == term.KEY_END:
            scroll[0] = max_scroll
        elif str(key).upper() in ("Q", "\x1b") or key.code == term.KEY_ESCAPE:
            break
