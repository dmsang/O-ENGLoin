"""awing/screens/menu.py — Interactive main menu."""
from awing import (term, bold, C_TITLE, C_BORDER, C_SEL, C_OK, C_ERR, C_WARN,
                   C_DIM, C_KEY, C_VAL, C_DBG, RST, render, center_in,
                   box_top, box_mid, box_bot, box_row, read_key,
                   is_mouse_click, mouse_row, LOGO, STATUS_COLORS,
                   _debug_on, _get_status, get_current_ssid)

MENU_ITEMS = [
    ("\u25b6  Auto Login",         "auto"),
    ("\u25a1  Run in Background",  "tray"),
    ("⎔  Network Test",         "nettest"),
    ("\u2b06  Check for Updates",  "update"),
    ("?  User Guide",              "help"),
    ("\u2665  Donate",             "donate"),
    ("\u26a1 Beta Features",      "beta"),
    ("\u2699  Settings",           "settings"),
    ("✗  Uninstall",          "uninstall"),
    ("\u2715  Exit",               "quit"),
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
        row += len(LOGO) + 1

        ssid = get_current_ssid() or "(not connected)"
        req = settings.get("required_ssid", "")
        sc2 = C_OK if ssid == req else C_ERR
        st = _get_status(); sc = STATUS_COLORS.get(st, C_DIM)
        dbg_tag = (" " + C_DBG + "[DEBUG ON]" + RST) if _debug_on[0] else ""
        info = (" WiFi:" + sc2 + ssid + RST +
                "  GW:" + C_VAL + settings["gateway"] + RST +
                "  Status:" + sc + st + RST + dbg_tag)
        rows[row] = center_in(info, W); row += 1 if (term.height or 24) <= 24 else 2

        bw = 50; bx = (W - bw) // 2
        rows[row]   = " " * bx + box_top(bw)
        rows[row+1] = " " * bx + box_row(bw, center_in(C_TITLE + bold(" MAIN MENU "), bw - 2))
        rows[row+2] = " " * bx + box_mid(bw)
        menu_row_ref[0] = row + 3
        for i, (label, action) in enumerate(MENU_ITEMS):
            suffix = ""
            if action == "tray" and tray_running: suffix = C_OK + " [running]" + RST
            content = (C_SEL + "  " + label + suffix + RST) if i == sel else (C_DIM + "  " + label + RST + suffix)
            rows[row+3+i] = " " * bx + box_row(bw, content)
        rows[row+3+n] = " " * bx + box_bot(bw)
        hr = row + 3 + n + 1
        hint = (C_KEY + "\u2191\u2193" + RST + " navigate   " + C_KEY + "Enter" + RST + " select   " +
                C_KEY + "Q" + RST + " quit")
        rows[hr] = center_in(hint, W)
        return rows

    while True:
        render(build())
        key = read_key()
        if key.code == term.KEY_UP:     sel = (sel - 1) % n
        elif key.code == term.KEY_DOWN: sel = (sel + 1) % n
        elif key.code == term.KEY_ENTER or str(key) in ("\n", "\r"):
            return MENU_ITEMS[sel][1]
        elif str(key).upper() == "Q": return "quit"
        elif is_mouse_click(key):
            idx = mouse_row(key) - menu_row_ref[0]
            if 0 <= idx < n:
                if idx == sel:
                    return MENU_ITEMS[sel][1]
                else:
                    sel = idx
