"""awing/screens/uninstall.py — Uninstallation logic and confirmation screen."""
import os, subprocess, sys
from awing import (term, bold, C_TITLE, C_BORDER, C_SEL, C_OK, C_ERR, C_WARN,
                   C_DIM, C_KEY, RST, render, center_in, box_top, box_mid,
                   box_bot, box_row, read_key, is_mouse_click, mouse_row,
                   mouse_col, exit_alt, show_cursor, stop_tray)
from awing.compat import IS_WIN
from .auto_login import stop_bg_worker

def perform_uninstall():
    try: stop_bg_worker()
    except Exception: pass
    try: stop_tray()
    except Exception: pass
    try: exit_alt()
    except Exception: pass
    try: show_cursor()
    except Exception: pass
    print(C_WARN + "\nUninstalling AWING Auto Login..." + RST)
    # 1. Desktop shortcut
    try:
        desk = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop", "AWING Auto Login.lnk")
        if os.path.exists(desk):
            os.remove(desk)
            print(C_OK + "  ✓ Desktop shortcut removed." + RST)
    except Exception: pass
    # 2. wifi.cmd
    try:
        wa = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WindowsApps", "wifi.cmd")
        if os.path.exists(wa):
            os.remove(wa)
            print(C_OK + "  ✓ 'wifi' command removed." + RST)
    except Exception: pass
    # 3. Schedule install directory cleanup
    try:
        inst_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "AWING-Login")
        if os.path.exists(inst_dir):
            cmd = f'timeout /t 1 /nobreak >nul & rmdir /s /q "{inst_dir}"'
            subprocess.Popen(["cmd.exe", "/c", cmd], creationflags=(subprocess.CREATE_NO_WINDOW if IS_WIN else 0))
            print(C_OK + "  ✓ App files scheduled for deletion." + RST)
    except Exception: pass
    print(C_OK + bold("\n✓ AWING Auto Login has been uninstalled successfully.\n") + RST)
    sys.exit(0)

def uninstall_screen():
    sel = [1]  # 0=Yes Uninstall, 1=Cancel
    def build():
        W = term.width or 80; H = term.height or 24
        bw = min(62, W - 4); bh = 14; bx = (W - bw) // 2; by = (H - bh) // 2
        rows = [""] * H
        rows[by]   = " " * bx + box_top(bw, " UNINSTALL ")
        rows[by+1] = " " * bx + box_row(bw, center_in(C_ERR + bold(" Completely Remove AWING Auto Login? ") + RST, bw - 2))
        rows[by+2] = " " * bx + box_mid(bw)
        rows[by+3] = " " * bx + box_row(bw, "  This will permanently remove:")
        rows[by+4] = " " * bx + box_row(bw, "  • Desktop shortcut ('AWING Auto Login')")
        rows[by+5] = " " * bx + box_row(bw, "  • 'wifi' terminal command")
        rows[by+6] = " " * bx + box_row(bw, "  • App files and saved configuration")
        rows[by+7] = " " * bx + box_mid(bw)
        b_yes = " Yes, Uninstall "; b_no = "   Cancel   "; gap = 4
        b0 = (C_ERR + bold(b_yes) + RST) if sel[0] == 0 else (C_DIM + b_yes + RST)
        b1 = (C_SEL + b_no + RST) if sel[0] == 1 else (C_DIM + b_no + RST)
        total = len(b_yes) + len(b_no) + gap; bb = (bw - total) // 2
        rows[by+8] = " " * bx + box_row(bw, " " * bb + b0 + " " * gap + b1)
        rows[by+9] = " " * bx + box_mid(bw)
        hint = C_KEY + "Left/Right" + RST + " select   " + C_KEY + "Enter" + RST + " confirm   " + C_KEY + "Esc" + RST + " cancel"
        rows[by+10] = " " * bx + box_row(bw, center_in(hint, bw - 2))
        for rr in range(by+11, by+13):
            rows[rr] = " " * bx + box_mid(bw)
        rows[by+13] = " " * bx + box_bot(bw)
        return rows

    while True:
        render(build())
        key = read_key()
        if not key: continue
        ks = str(key).upper()
        activate_u = False
        if is_mouse_click(key):
            W3=term.width or 80; H3=term.height or 24
            bw3=min(62,W3-4); bx3=(W3-bw3)//2; by3=(H3-14)//2
            if mouse_row(key) == by3+8:
                b_yes=" Yes, Uninstall "; b_no="   Cancel   "; gap3=4
                total_u=len(b_yes)+len(b_no)+gap3; bb3=bx3+1+(bw3-total_u)//2
                mc3=mouse_col(key)
                if bb3 <= mc3 < bb3+len(b_yes): sel[0]=0; activate_u=True
                elif bb3+len(b_yes)+gap3 <= mc3 < bb3+total_u: sel[0]=1; activate_u=True
        if key.code in (term.KEY_LEFT, term.KEY_RIGHT):
            sel[0] = 1 - sel[0]
        elif activate_u or key.code == term.KEY_ENTER or ks in ("\n", "\r"):
            return (sel[0] == 0)
        elif ks in ("Q", "\x1b") or key.code == term.KEY_ESCAPE:
            return False
