"""awing/screens/menu.py — Interactive main menu."""
from awing import (term, bold, C_TITLE, C_BORDER, C_SEL, C_OK, C_ERR, C_WARN,
                   C_DIM, C_KEY, C_VAL, C_DBG, RST, render, center_in,
                   box_top, box_mid, box_bot, box_row, read_key, str_width,
                   is_mouse_click, mouse_row, LOGO, APP_VERSION, STATUS_COLORS,
                   _debug_on, _get_status, _format_remaining_tag, get_current_ssid)

MENU_ITEMS = [
    ("▶  Start Auto Login",         "auto"),
    ("⧉  Run in Background (Tray)", "tray"),
    ("⚡ Network Speed & Ping Test", "nettest"),
    ("⬆  Check for Updates",        "update"),
    ("ℹ  User Guide",               "help"),
    ("♥  Donate / Support",         "donate"),
    ("⚙  Settings & Themes",        "settings"),
    ("◎  Beta Features",            "beta"),
    ("✕  Uninstall",                "uninstall"),
    ("⏻  Exit",                     "quit"),
]

def main_menu(settings, tray_running=False):
    sel = 0; n = len(MENU_ITEMS)
    menu_row_ref = [0]

    def build():
        W = term.width or 80
        H = max(term.height or 24, 25)
        rows = [""] * H
        row = 0 if (term.height or 24) <= 24 else 1

        logo_w = len(LOGO[0])
        logo_pad = " " * max(0, (W - logo_w) // 2)
        for i, line in enumerate(LOGO):
            rows[row + i] = logo_pad + C_TITLE + line + RST
        row += len(LOGO)

        # Subtitle banner
        sub = C_DIM + "✦ High-Speed Captive Portal Assistant ✦" + RST
        rows[row] = center_in(sub, W)
        row += 1 if (term.height or 24) <= 24 else 2

        # Status info bar
        ssid = get_current_ssid() or "(not connected)"
        req = settings.get("required_ssid", "")
        sc2 = C_OK if ssid == req else C_ERR
        st = _get_status(); sc = STATUS_COLORS.get(st, C_DIM)
        dbg_tag = (" " + C_DBG + "[DEBUG]" + RST) if _debug_on[0] else ""
        rem_tag = _format_remaining_tag(compact=False, show_bar=True)
        info = ("WiFi: " + sc2 + ssid + RST +
                "  GW: " + C_VAL + settings.get("gateway", "192.168.200.1") + RST +
                "  Status: " + sc + bold(st) + RST + rem_tag + dbg_tag)
        rows[row] = center_in(info, W)
        row += 1 if (term.height or 24) <= 24 else 2

        # Menu Box
        bw = min(56, W - 4); bx = (W - bw) // 2
        rows[row] = " " * bx + box_top(bw, "✦ MAIN MENU ✦")
        menu_row_ref[0] = row + 1

        for i, (label, action) in enumerate(MENU_ITEMS):
            suffix = ""
            if action == "tray" and tray_running:
                suffix = C_OK + " [running]" + RST
            pad_lbl = label + " " * max(0, 36 - str_width(label))
            if i == sel:
                content = C_SEL + "  " + pad_lbl + suffix + RST
            else:
                content = "  " + label + suffix
            rows[row + 1 + i] = " " * bx + box_row(bw, content)

        rows[row + 1 + n] = " " * bx + box_bot(bw)

        hr = row + 1 + n + 1
        hint = (C_KEY + "↑↓" + RST + " navigate   " +
                C_KEY + "Enter" + RST + " select   " +
                C_KEY + "Q" + RST + " quit")
        rows[hr] = center_in(hint, W)
        return rows

    while True:
        render(build())
        with term.cbreak():
            key = term.inkey(timeout=1.0)
        if not key:
            continue

        if is_mouse_click(key):
            my = mouse_row(key)
            base_r = menu_row_ref[0]
            if base_r <= my < base_r + n:
                sel = my - base_r
                return MENU_ITEMS[sel][1]

        if key.code == term.KEY_UP:
            sel = (sel - 1) % n
        elif key.code == term.KEY_DOWN:
            sel = (sel + 1) % n
        elif key.code == term.KEY_ENTER or str(key) in ("\n", "\r"):
            return MENU_ITEMS[sel][1]
        elif str(key).upper() in ("Q", "\x1b") or key.code == term.KEY_ESCAPE:
            return "quit"
