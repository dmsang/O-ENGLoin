"""awing/screens/wifi_popup.py — WiFi warning modal."""
import time
from awing import (term, bold, C_TITLE, C_BORDER, C_SEL, C_OK, C_ERR, C_WARN,
                   C_DIM, C_KEY, RST, render, center_in, box_top, box_mid,
                   box_bot, box_row, read_key, is_mouse_click, mouse_row,
                   mouse_col, get_current_ssid, get_available_ssids,
                   connect_to_ssid)

def check_wifi_popup(settings):
    required = settings.get("required_ssid","").strip()
    if not required: return True
    current  = get_current_ssid(force=True)
    dbg("[wifi_popup] current="+str(current)+" required="+required)
    if current==required: return True

    avail   = get_available_ssids()
    has_net = required in avail
    sel        = [0]; msg=[""]   # 0=Connect, 1=Skip, 2=Exit
    current_ref= [current]

    def build():
        W=term.width or 80; H=term.height or 24
        bw=min(62,W-4); bh=14; bx=(W-bw)//2; by=(H-bh)//2
        rows=[""]*H
        rows[by]  =" "*bx+box_top(bw," WIFI WARNING ")
        rows[by+1]=" "*bx+box_row(bw,center_in(C_WARN+bold(" Wrong WiFi network!"),bw-2))
        rows[by+2]=" "*bx+box_mid(bw)
        cur_disp = current_ref[0] or "(not connected)"
        rows[by+3]=" "*bx+box_row(bw," Current   : "+C_ERR+cur_disp+RST)
        rows[by+4]=" "*bx+box_row(bw," Required  : "+C_OK+required+RST)
        note=" WiFi available - can connect automatically." if has_net else " WiFi not found nearby."
        rows[by+5]=" "*bx+box_row(bw,C_DIM+note+RST)
        rows[by+6]=" "*bx+box_mid(bw)
        rows[by+7]=" "*bx+box_row(bw,(C_WARN+msg[0]+RST) if msg[0] else "")
        rows[by+8]=" "*bx+box_mid(bw)
        btn_ok=" Connect "; btn_sk=" Skip "; btn_ex=" Exit "
        gap=2
        total=len(btn_ok)+len(btn_sk)+len(btn_ex)+gap*2
        bb=(bw-total)//2
        b0=C_SEL+btn_ok+RST if sel[0]==0 else C_DIM+btn_ok+RST
        b1=C_SEL+btn_sk+RST if sel[0]==1 else C_DIM+btn_sk+RST
        b2=C_SEL+btn_ex+RST if sel[0]==2 else C_DIM+btn_ex+RST
        btns=" "*bb+b0+" "*gap+b1+" "*gap+b2
        rows[by+9] =" "*bx+box_row(bw,btns)
        rows[by+10]=" "*bx+box_mid(bw)
        hint=C_KEY+"Left/Right"+RST+" select   "+C_KEY+"Enter"+RST+" confirm   "+C_KEY+"Esc"+RST+" exit"
        rows[by+11]=" "*bx+box_row(bw,center_in(hint,bw-2))
        rows[by+12]=" "*bx+box_mid(bw)
        rows[by+13]=" "*bx+box_bot(bw)
        return rows

    while True:
        render(build())
        key=read_key(); ks=str(key).upper()
        n_btn=3 if has_net else 2

        # Mouse: click on button row (by+9)
        activate = False
        if is_mouse_click(key):
            W=term.width or 80; H=term.height or 24
            bw=min(62,W-4); bh=14; bx=(W-bw)//2; by=(H-bh)//2
            if mouse_row(key) == by+9:
                # Compute button x-positions to determine which was clicked
                btn_ok=" Connect "; btn_sk=" Skip "; btn_ex=" Exit "
                gap=2
                total_b=len(btn_ok)+len(btn_sk)+len(btn_ex)+gap*2
                bb=bx+1+(bw-total_b)//2   # left edge of first button (inside box)
                mc=mouse_col(key)
                x0=bb; x1=x0+len(btn_ok)
                x2=x1+gap; x3=x2+len(btn_sk)
                x4=x3+gap; x5=x4+len(btn_ex)
                if x0 <= mc < x1 and has_net: sel[0]=0; activate=True
                elif x2 <= mc < x3: sel[0]=1; activate=True
                elif x4 <= mc < x5: sel[0]=2; activate=True

        if key.code in (term.KEY_LEFT,term.KEY_TAB,term.KEY_BTAB):
            sel[0]=(sel[0]-1)%n_btn
        elif key.code==term.KEY_RIGHT:
            sel[0]=(sel[0]+1)%n_btn
        elif activate or key.code==term.KEY_ENTER or ks in ("\n","\r"):
            if sel[0]==2: return False        # Exit
            if sel[0]==1: return True          # Skip - enter app without correct wifi
            if not has_net: msg[0]="WiFi not available!"; continue
            msg[0]="Connecting to \""+required+"\"..."
            render(build())
            ok=connect_to_ssid(required)
            if ok:
                time.sleep(4)
                new_ssid=get_current_ssid(force=True)
                current_ref[0]=new_ssid
                if new_ssid==required: return True
                msg[0]="Connect failed ("+str(new_ssid)+"). Please retry."
            else:
                msg[0]="Connection command failed."
        elif key.code==term.KEY_ESCAPE or ks=="Q":
            return False
