"""awing/screens/auto_login.py — Real-time auto-login screen and BG worker."""
from awing.beta import should_preempt
import threading, time
from awing import (term, bold, C_TITLE, C_BORDER, C_SEL, C_OK, C_ERR, C_WARN,
                   C_DIM, C_KEY, C_VAL, C_DBG, RST, render, center_in,
                   box_top, box_mid, box_bot, box_row, sep_row,
                   is_mouse_click, mouse_scroll_up, mouse_scroll_down,
                   APP_VERSION, SPIN, STATUS_COLORS, LOG_COLORS, LOG_ICONS,
                   _debug_on, _tray_quit, _logs, _log_lock, _last_login_time,
                   _set_status, _get_status, _add_log, _last_login_str,
                   get_current_ssid, has_internet, do_login)

def dbg(msg):
    if _debug_on[0]: _add_log("DBG", msg)

def run_auto_login_screen(settings, bg_stop=None):
    scroll=[0]; spin_i=[0]; local_stop=threading.Event()

    def worker():
        chk=settings["check_interval"]; ret=settings["retry_interval"]
        while not local_stop.is_set():
            _set_status("CHECKING",notify=False)
            dbg("[worker] Checking internet connection...")
            if has_internet(settings):
                _set_status("ONLINE")
                if should_preempt(settings):
                    _add_log("INFO", "[PREEMPT] Session expiring — renewing early...")
                    do_login(settings, _add_log)
                dbg("[worker] Internet OK - next check in "+str(chk)+"s")
                for _ in range(chk*2):
                    if local_stop.is_set(): return
                    time.sleep(0.5)
            else:
                _set_status("OFFLINE")
                _add_log("WARN","Internet lost - attempting login...")
                _set_status("LOGGING IN",notify=False)
                ok=do_login(settings,_add_log)
                if ok:
                    _last_login_time[0] = time.time()
                    _set_status("ONLINE")
                    _add_log("OK","Reconnected! Next check in "+str(chk)+"s")
                    for _ in range(chk*2):
                        if local_stop.is_set(): return
                        time.sleep(0.5)
                else:
                    _set_status("OFFLINE")
                    _add_log("ERR","Login failed - retrying in "+str(ret)+"s")
                    for _ in range(ret*2):
                        if local_stop.is_set(): return
                        time.sleep(0.5)

    if bg_stop is None:
        wt=threading.Thread(target=worker,daemon=True); wt.start()
    else:
        wt=None

    def build():
        W=term.width or 80; H=term.height or 24
        LOG_Y=4
        st=_get_status(); sc=STATUS_COLORS.get(st,C_DIM)
        spin=SPIN[spin_i[0]%len(SPIN)]; spin_i[0]+=1
        gw=settings["gateway"]; chk=settings["check_interval"]; ret=settings["retry_interval"]
        ssid=get_current_ssid() or "(N/A)"
        req=settings.get("required_ssid","")
        sc2=C_OK if ssid==req else C_WARN
        dbg_tag=(" "+C_DBG+"[DEBUG]"+RST) if _debug_on[0] else ""

        # rows chia: 0=top, 1=title, 2=info, 3=sep, 4..LOG_Y+LOG_H-1=logs, sep=LOG_Y+LOG_H, sep+1=hint, sep+2=bot
        # sep+2 = 4+LOG_H+2 = LOG_H+6 = H-1 khi LOG_H=H-7
        LOG_H=H-7  # 4 header rows + separator + hint + bot = 7
        rows=[""]*(H)
        rows[0]=box_top(W)
        rows[1]=box_row(W,center_in(C_TITLE+bold(" AWING Auto Login v"+APP_VERSION+" ")+dbg_tag,W-2))
        info=(" GW:"+C_VAL+gw+RST+" WiFi:"+sc2+ssid+RST+
              " Status:"+sc+bold(st)+RST+sc+" "+spin+RST+
              C_DIM+" chk="+str(chk)+"s ret="+str(ret)+"s"+RST+
              _last_login_str())
        rows[2]=box_row(W,info)
        rows[3]=sep_row(W)

        with _log_lock:
            total=len(_logs); start=scroll[0]
            visible=list(_logs[start:start+LOG_H])

        for i in range(LOG_H):
            if i<len(visible):
                ts,lvl,msg=visible[i]
                c=LOG_COLORS.get(lvl,C_DIM); ic=LOG_ICONS.get(lvl," ")
                content=" "+C_DIM+ts+RST+" "+c+ic+" "+msg+RST
            else:
                content=""
            rows[LOG_Y+i]=box_row(W,content)

        sep=LOG_Y+LOG_H
        rows[sep]=sep_row(W)

        is_bg=bg_stop is not None
        if total>LOG_H:
            sb=C_DIM+"("+str(start+1)+"-"+str(min(start+LOG_H,total))+"/"+str(total)+")"+RST
        else:
            sb=""
        if is_bg:
            hint=(C_KEY+"\u2191\u2193"+RST+" scroll "+sb+
                  "  "+C_KEY+"End"+RST+" jump to bottom"+
                  "  "+C_KEY+"Q/Esc"+RST+" hide to tray"+
                  "  "+C_KEY+"X"+RST+" stop worker")
        else:
            hint=(C_KEY+"\u2191\u2193"+RST+" scroll "+sb+
                  "  "+C_KEY+"End"+RST+" jump to bottom"+
                  "  "+C_KEY+"Q/Esc"+RST+" back to menu")
        rows[sep+1]=box_row(W," "+hint)
        rows[sep+2]=box_bot(W)
        return rows

    try:
        while True:
            if _tray_quit.is_set(): break
            render(build())
            with term.cbreak(): key=term.inkey(timeout=0.35)
            if key:
                ks=str(key).upper()
                if key.code==term.KEY_ESCAPE or ks=="Q": break
                elif ks=="X" and bg_stop is not None: bg_stop.set(); break
                elif key.code==term.KEY_UP or mouse_scroll_up(key):
                    with _log_lock: scroll[0]=max(0,scroll[0]-1)
                elif key.code==term.KEY_DOWN or mouse_scroll_down(key):
                    with _log_lock:
                        _lh=(term.height or 24)-7
                        total=len(_logs)
                        scroll[0]=min(max(0,total-_lh),scroll[0]+1)
                elif key.code==term.KEY_END or ks=="G":
                    with _log_lock:
                        _lh=(term.height or 24)-7
                        scroll[0]=max(0,len(_logs)-_lh)
                elif key.code==term.KEY_HOME:
                    scroll[0]=0
    finally:
        local_stop.set()
        if wt: wt.join(timeout=3)

# ── Background worker ─────────────────────────────────────────────────────────
_bg_stop   = threading.Event()
_bg_thread = [None]

def start_bg_worker(settings):
    _bg_stop.clear()
    def worker():
        chk=settings["check_interval"]; ret=settings["retry_interval"]
        while not _bg_stop.is_set():
            _set_status("CHECKING",notify=False)
            dbg("[bg_worker] Checking connection...")
            if has_internet(settings):
                _set_status("ONLINE")
                if should_preempt(settings):
                    _add_log("INFO", "[BG-PREEMPT] Renewing session before timeout...")
                    do_login(settings, _add_log)
                dbg("[bg_worker] Internet OK")
                for _ in range(chk*2):
                    if _bg_stop.is_set(): return
                    time.sleep(0.5)
            else:
                _set_status("OFFLINE")
                _add_log("WARN","[BG] Internet lost - logging in...")
                _set_status("LOGGING IN",notify=False)
                ok=do_login(settings,_add_log)
                if ok:
                    _last_login_time[0] = time.time()
                    _set_status("ONLINE")
                    _add_log("OK","[BG] Login successful!")
                    for _ in range(chk*2):
                        if _bg_stop.is_set(): return
                        time.sleep(0.5)
                else:
                    _set_status("OFFLINE")
                    _add_log("ERR","[BG] Login failed")
                    for _ in range(ret*2):
                        if _bg_stop.is_set(): return
                        time.sleep(0.5)
    t=threading.Thread(target=worker,daemon=True); t.start(); _bg_thread[0]=t

def stop_bg_worker():
    _bg_stop.set()
    if _bg_thread[0]: _bg_thread[0].join(timeout=3)
