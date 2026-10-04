"""awing/screens/menu.py — Interactive main menu."""
from awing import (term, bold, C_TITLE, C_BORDER, C_SEL, C_OK, C_ERR, C_WARN,
                   C_DIM, C_KEY, C_VAL, C_DBG, RST, render, center_in,
                   box_top, box_mid, box_bot, box_row, read_key,
                   is_mouse_click, mouse_row, LOGO, STATUS_COLORS,
                   _debug_on, _get_status, get_current_ssid)

MENU_ITEMS=[
    ("\u25b6  Auto Login",         "auto"),
    ("\u25a1  Run in Background",  "tray"),
    ("⎔  Network Test",         "nettest"),
    ("\u2b06  Check for Updates",  "update"),
    ("?  User Guide",              "help"),
    ("\u2699  Settings",           "settings"),
    ("✗  Uninstall",          "uninstall"),
    ("\u2715  Exit",               "quit"),
]

def main_menu(settings, tray_running=False):
    sel=0; n=len(MENU_ITEMS)

    menu_row_ref = [0]  # absolute screen row of first menu item

    def build():
        W=term.width or 80; H=term.height or 24
        rows=[""]*H
        row=1
        logo_w=len(LOGO[0])
        logo_pad=" "*max(0,(W-logo_w)//2)
        for i,line in enumerate(LOGO):
            rows[row+i]=logo_pad+C_TITLE+line+RST
        row+=len(LOGO)+1

        ssid=get_current_ssid() or "(not connected)"
        req=settings.get("required_ssid","")
        sc2=C_OK if ssid==req else C_ERR
        st=_get_status(); sc=STATUS_COLORS.get(st,C_DIM)
        dbg_tag=(" "+C_DBG+"[DEBUG ON]"+RST) if _debug_on[0] else ""
        info=(" WiFi:"+sc2+ssid+RST+
              "  GW:"+C_VAL+settings["gateway"]+RST+
              "  Status:"+sc+st+RST+dbg_tag)
        rows[row]=center_in(info,W); row+=2

        bw=50; bh=len(MENU_ITEMS)+4; bx=(W-bw)//2
        rows[row]   =" "*bx+box_top(bw)
        rows[row+1] =" "*bx+box_row(bw,center_in(C_TITLE+bold(" MAIN MENU "),bw-2))
        rows[row+2] =" "*bx+box_mid(bw)
        menu_row_ref[0] = row + 3   # first item row (0-indexed from top of terminal)
        for i,(label,action) in enumerate(MENU_ITEMS):
            suffix=""
            if action=="tray" and tray_running: suffix=C_OK+" [running]"+RST
            content=(C_SEL+"  "+label+suffix+RST) if i==sel else (C_DIM+"  "+label+RST+suffix)
            rows[row+3+i]=" "*bx+box_row(bw,content)
        rows[row+3+len(MENU_ITEMS)]=" "*bx+box_bot(bw)
        hr=row+3+len(MENU_ITEMS)+1
        hint=(C_KEY+"\u2191\u2193"+RST+" navigate   "+C_KEY+"Enter"+RST+" select   "+
              C_KEY+"Q"+RST+" quit")
        rows[hr]=center_in(hint,W)
        return rows

    while True:
        render(build())
        key=read_key()
        if key.code==term.KEY_UP:     sel=(sel-1)%n
        elif key.code==term.KEY_DOWN: sel=(sel+1)%n
        elif key.code==term.KEY_ENTER or str(key) in ("\n","\r"):
            return MENU_ITEMS[sel][1]
        elif str(key).upper()=="Q": return "quit"
        elif is_mouse_click(key):
            idx = mouse_row(key) - menu_row_ref[0]
            if 0 <= idx < n:
                if idx == sel:
                    return MENU_ITEMS[sel][1]   # second click on selected = confirm
                else:
                    sel = idx                   # first click = hover/highlight
