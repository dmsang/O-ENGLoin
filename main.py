import os, re, sys, time, json, threading, subprocess, traceback, zipfile, urllib.request
import requests
import speedtest as _speedtest_lib
from bs4 import BeautifulSoup
from blessed import Terminal
import pystray
from PIL import Image, ImageDraw

if sys.platform == "win32":
    import ctypes
    _k = ctypes.windll.kernel32
    _k.SetConsoleMode(_k.GetStdHandle(-11), 7)

sys.stdout.reconfigure(encoding="utf-8")
term = Terminal()

# ── Console window handle (for hide/show) ─────────────────────────────────────
_HWND = [0]

def _get_hwnd():
    if _HWND[0] == 0:
        _HWND[0] = ctypes.windll.kernel32.GetConsoleWindow()
    return _HWND[0]

def hide_console():
    hwnd = _get_hwnd()
    if hwnd: ctypes.windll.user32.ShowWindow(hwnd, 0)   # SW_HIDE

def show_console():
    hwnd = _get_hwnd()
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 9)         # SW_RESTORE
        ctypes.windll.user32.SetForegroundWindow(hwnd)

# ── ANSI ──────────────────────────────────────────────────────────────────────
RST = "\033[0m"
def fg(r,g,b): return "\033[38;2;%d;%d;%dm"%(r,g,b)
def bg(r,g,b): return "\033[48;2;%d;%d;%dm"%(r,g,b)
def bold(s):   return "\033[1m"+s+RST

C_TITLE  = fg(100,200,255)
C_BORDER = fg(60,100,160)
C_SEL    = bg(30,80,160)+fg(255,255,255)
C_OK     = fg(80,200,120)
C_ERR    = fg(220,80,80)
C_WARN   = fg(240,180,50)
C_DIM    = fg(120,120,140)
C_KEY    = fg(180,220,255)
C_VAL    = fg(200,230,255)
C_DBG    = fg(180,120,255)

LOGO = [
    " _____        _____ _   _  _____   _            _       ",
    "|  _  |      |  ___| \\ | ||  __ \\ | |          (_)      ",
    "| | | |______| |__ |  \\| || |  \\/ | |     ___   _ _ __  ",
    "| | | |______|  __|| . ` || | __  | |    / _ \\ | | '_ \\ ",
    "\\ \\_/ /      | |___| |\\  || |_\\ \\ | |___| (_) || | | | |",
    " \\___/       \\____/\\_| \\_/ \\____/ \\_____/\\___/ |_|_| |_|",
]
APP_VERSION  = "1.0.3"
GITHUB_REPO  = "dmsang/O-ENGLoin"

SPIN = ["\u280b","\u2819","\u2839","\u2838","\u283c","\u2834","\u2826","\u2827","\u2807","\u280f"]

# ── Screen rendering ───────────────────────────────────────────────────────────
def strip_ansi(s): return re.sub(r"\033\[[^m]*m","",s)
def hide_cursor(): sys.stdout.write("\033[?25l"); sys.stdout.flush()
def show_cursor(): sys.stdout.write("\033[?25h"); sys.stdout.flush()
def enter_alt():   sys.stdout.write("\033[?1049h\033[2J\033[H"); sys.stdout.flush()
def exit_alt():    sys.stdout.write("\033[?1049l"); sys.stdout.flush()

def render(rows: list):
    W = term.width or 80
    out = ["\033[?2026h", "\033[H"]
    for i, row in enumerate(rows):
        plain = strip_ansi(row)
        pad   = W - len(plain)
        out.append(row + (" "*pad if pad > 0 else ""))
        if i < len(rows)-1:
            out.append("\n")
    out.append("\033[?2026l")
    sys.stdout.write("".join(out))
    sys.stdout.flush()

def center_in(text, width):
    plain = strip_ansi(text)
    pad   = max(0, width - len(plain))
    return " "*(pad//2) + text

def box_top(w, title=""):
    inner = w-2
    if title:
        t = " "+title+" "; pad = inner-len(t)
        top = "\u2500"*(pad//2)+t+"\u2500"*(pad-pad//2)
    else:
        top = "\u2500"*inner
    return C_BORDER+"\u250c"+top+"\u2510"+RST

def box_mid(w):
    return C_BORDER+"\u2502"+RST+" "*(w-2)+C_BORDER+"\u2502"+RST

def box_bot(w):
    return C_BORDER+"\u2514"+"\u2500"*(w-2)+"\u2518"+RST

def box_row(w, content):
    inner = w-2
    plain = strip_ansi(content)
    if len(plain) > inner:
        # Truncate plain text den inner-3, giu ANSI bang cach rebuild
        target  = inner-3
        count   = 0
        out     = []
        i       = 0
        while i < len(content):
            # skip ANSI escape sequence
            if content[i] == "\033" and i+1 < len(content) and content[i+1] == "[":
                j = i+2
                while j < len(content) and content[j] not in "m":
                    j += 1
                out.append(content[i:j+1])
                i = j+1
            else:
                if count < target:
                    out.append(content[i])
                    count += 1
                i += 1
        content = "".join(out) + RST + "..."
        plain   = strip_ansi(content)
    padded = content + " "*max(0, inner-len(plain))
    return C_BORDER+"\u2502"+RST+padded+C_BORDER+"\u2502"+RST

def sep_row(w):
    return C_BORDER+"\u251c"+"\u2500"*(w-2)+"\u2524"+RST

# ── Settings ──────────────────────────────────────────────────────────────────
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

DEFAULT_SETTINGS = {
    "gateway"        : "192.168.200.1",
    "awing_login_url": "http://v1.awingconnect.vn/login",
    "check_url"      : "http://connectivitycheck.gstatic.com/generate_204",
    "check_interval" : 15,
    "retry_interval" : 5,
    "request_timeout": 10,
    "required_ssid"  : "INET - Free WiFi",
    "notifications"  : False,
    "debug"          : False,
}
SETTING_LABELS = {
    "gateway"        : "Default Gateway",
    "awing_login_url": "AWING Login URL",
    "check_url"      : "Check URL",
    "check_interval" : "Check Interval (s)",
    "retry_interval" : "Retry Interval (s)",
    "request_timeout": "Request Timeout (s)",
    "required_ssid"  : "Required WiFi SSID",
    "notifications"  : "Notifications (tray)",
    "debug"          : "Debug Mode",
}
SETTING_KEYS = list(SETTING_LABELS.keys())

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE,"r",encoding="utf-8") as f:
                saved = json.load(f)
            s = dict(DEFAULT_SETTINGS); s.update(saved); return s
        except Exception: pass
    return dict(DEFAULT_SETTINGS)

def save_settings(settings):
    try:
        with open(SETTINGS_FILE,"w",encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        return True
    except Exception: return False

# ── Debug logger ──────────────────────────────────────────────────────────────
_debug_on   = [False]
_ssid_cache = [None, 0.0]   # [ssid, timestamp]
SSID_TTL    = 10.0          # chi goi netsh moi 10 giay

def dbg(msg):
    if _debug_on[0]:
        _add_log("DBG", msg)

# ── WiFi ──────────────────────────────────────────────────────────────────────
def _fetch_ssid():
    try:
        out = subprocess.check_output(
            ["netsh","wlan","show","interfaces"],
            encoding="utf-8", errors="ignore",
            creationflags=subprocess.CREATE_NO_WINDOW)
        dbg("[wifi] netsh interfaces: "+str(len(out))+" bytes")
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("SSID") and "BSSID" not in line:
                parts = line.split(":",1)
                if len(parts)==2: return parts[1].strip()
    except Exception as e:
        dbg("[wifi] get_current_ssid error: "+str(e))
    return None

def get_current_ssid(force=False):
    now = time.time()
    if force or (now - _ssid_cache[1]) >= SSID_TTL:
        _ssid_cache[0] = _fetch_ssid()
        _ssid_cache[1] = now
    return _ssid_cache[0]

def get_available_ssids():
    try:
        out = subprocess.check_output(
            ["netsh","wlan","show","networks","mode=bssid"],
            encoding="utf-8", errors="ignore",
            creationflags=subprocess.CREATE_NO_WINDOW)
        ssids=[]
        for line in out.splitlines():
            line=line.strip()
            if line.startswith("SSID") and "BSSID" not in line:
                parts=line.split(":",1)
                if len(parts)==2:
                    s=parts[1].strip()
                    if s: ssids.append(s)
        dbg("[wifi] available: "+str(ssids))
        return ssids
    except Exception as e:
        dbg("[wifi] get_available_ssids error: "+str(e))
        return []

def connect_to_ssid(ssid):
    try:
        dbg("[wifi] connecting to: "+ssid)
        r = subprocess.run(
            ["netsh","wlan","connect","name="+ssid],
            encoding="utf-8", errors="ignore", capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=15)
        dbg("[wifi] connect returncode: "+str(r.returncode)+" stdout: "+r.stdout.strip())
        return r.returncode==0
    except Exception as e:
        dbg("[wifi] connect error: "+str(e))
        return False

# ── System tray ───────────────────────────────────────────────────────────────
_ICON_COLORS = {
    "ONLINE"    :(80,200,120),
    "OFFLINE"   :(220,80,80),
    "LOGGING IN":(240,180,50),
    "CHECKING"  :(100,160,220),
}
def make_tray_icon(status="OFFLINE"):
    color = _ICON_COLORS.get(status,(150,150,150))
    img = Image.new("RGBA",(64,64),(0,0,0,0))
    d   = ImageDraw.Draw(img)
    d.ellipse([1,1,62,62], fill=color+(255,))
    cx,cy = 32,38
    for radius,width in [(22,4),(14,4),(6,4)]:
        d.arc([cx-radius,cy-radius,cx+radius,cy+radius],200,340,
              fill=(255,255,255,230),width=width)
    d.ellipse([cx-4,cy-4,cx+4,cy+4],fill=(255,255,255,255))
    return img

_tray_ref  = [None]
_tray_show = threading.Event()
_tray_quit = threading.Event()
_notif_on  = [False]

def _tray_update(status):
    icon = _tray_ref[0]
    if icon is None: return
    try: icon.icon=make_tray_icon(status); icon.title="AWING - "+status
    except Exception: pass

def _notify(title, msg):
    if not _notif_on[0]: return
    icon = _tray_ref[0]
    if icon:
        try: icon.notify(msg, title)
        except Exception: pass

def start_tray():
    def on_open(icon,item):
        _tray_show.set()
        show_console()
    def on_quit(icon,item):
        _tray_quit.set(); icon.stop()
    menu = pystray.Menu(
        pystray.MenuItem('Open window', on_open, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", on_quit),
    )
    icon = pystray.Icon("AWING",make_tray_icon("OFFLINE"),"AWING Login",menu)
    _tray_ref[0] = icon
    threading.Thread(target=icon.run, daemon=True).start()

def stop_tray():
    icon = _tray_ref[0]
    if icon:
        try: icon.stop()
        except Exception: pass

# ── Shared log + status ───────────────────────────────────────────────────────
MAX_LOGS     = 500
_logs        = []
_log_lock    = threading.Lock()
_status      = ["OFFLINE"]
_status_lock = threading.Lock()

def _add_log(level, msg):
    ts = time.strftime("%H:%M:%S")
    with _log_lock:
        _logs.append((ts,level,msg))
        if len(_logs)>MAX_LOGS: _logs.pop(0)

def _set_status(s, notify=True):
    with _status_lock:
        prev = _status[0]; _status[0] = s
    _tray_update(s)
    dbg("[status] "+prev+" -> "+s)
    if notify and s!=prev:
        if s=="ONLINE" and prev in ("OFFLINE","LOGGING IN"):
            _notify("AWING Login","\u2713 Internet connected!")
        elif s=="OFFLINE" and prev=="ONLINE":
            _notify("AWING Login","\u26a0 Internet disconnected!")

def _get_status():
    with _status_lock: return _status[0]

# ── Network ───────────────────────────────────────────────────────────────────
def create_session():
    s = requests.Session()
    s.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"})
    return s

def has_internet(settings):
    url = settings["check_url"]; tmo = settings["request_timeout"]
    try:
        t0 = time.time()
        r  = requests.get(url, timeout=tmo, allow_redirects=False)
        dbg("[inet] GET "+url+" -> "+str(r.status_code)+" (%.0fms)"%(1000*(time.time()-t0)))
        return r.status_code==204
    except Exception as e:
        dbg("[inet] error: "+str(e))
        return False

def get_captive_info(session, settings):
    gw  = settings["gateway"]; tmo = settings["request_timeout"]
    url = "http://"+gw+"/login"
    dbg("[captive] GET "+url)
    t0  = time.time()
    r   = session.get(url, timeout=tmo); r.raise_for_status()
    dbg("[captive] status="+str(r.status_code)+" len="+str(len(r.text))+" (%.0fms)"%(1000*(time.time()-t0)))
    soup= BeautifulSoup(r.text,"html.parser")
    form= soup.select_one("#authForm")
    if not form: raise RuntimeError("Cannot find #authForm")
    def val(id_):
        el = form.select_one("#"+id_)
        if not el: raise RuntimeError("Cannot find #"+id_)
        v = el.get("value","")
        dbg("[captive] "+id_+"="+v[:20])
        return v
    return {"serial":val("serial"),"client_mac":val("client_mac"),
            "client_ip":val("client_ip"),"userurl":val("userurl"),
            "login_url":val("login_url"),"chap_id":val("chap-id"),
            "chap_challenge":val("chap-challenge")}, r.url

def do_login(settings, log_cb):
    gw=settings["gateway"]; tmo=settings["request_timeout"]
    if not gw: log_cb("ERR","No default gateway configured"); return False
    session=create_session()
    try:
        log_cb("INFO","Connecting to gateway "+gw+"...")
        captive,_=get_captive_info(session,settings)
        log_cb("INFO","MAC:"+captive["client_mac"]+" IP:"+captive["client_ip"])

        dbg("[login] GET awing url")
        t0=time.time()
        r=session.get(settings["awing_login_url"],params=captive,timeout=tmo)
        r.raise_for_status()
        dbg("[login] awing status="+str(r.status_code)+" url="+r.url+" (%.0fms)"%(1000*(time.time()-t0)))
        awing_url=r.url

        verify=settings["awing_login_url"].replace("/login","/Home/VerifyUrl")
        dbg("[login] POST VerifyUrl")
        t0=time.time()
        r=session.post(verify,headers={"X-Requested-With":"XMLHttpRequest","Referer":awing_url},timeout=tmo)
        r.raise_for_status()
        dbg("[login] verify status="+str(r.status_code)+" (%.0fms)"%(1000*(time.time()-t0)))
        dbg("[login] verify body="+r.text[:200])

        data=r.json(); ctx=data["captiveContext"]
        campaign=ctx["campaignData"]
        log_cb("INFO","Session:"+str(campaign["sessionId"])[:12]+"...")
        dbg("[login] workspaceId="+str(campaign.get("workspaceId","")))

        auth=ctx.get("contentAuthenForm")
        if not auth: raise RuntimeError("No contentAuthenForm in response")
        soup=BeautifulSoup(auth,"html.parser")
        form=soup.select_one("#frmLogin")
        if not form: raise RuntimeError("Cannot find #frmLogin")
        action=form.get("action")
        if not action: raise RuntimeError("Form has no action")
        fd={el.get("name"):el.get("value","") for el in form.select("input") if el.get("name")}
        dbg("[login] form action="+action)
        dbg("[login] form fields="+str(list(fd.keys())))
        log_cb("INFO","Logging in as: "+str(fd.get("username","?")))

        dbg("[login] POST form -> "+action)
        t0=time.time()
        r2=session.post(action,data=fd,headers={"Referer":awing_url},allow_redirects=True,timeout=tmo)
        dbg("[login] form post status="+str(r2.status_code)+" final="+r2.url+" (%.0fms)"%(1000*(time.time()-t0)))
        dbg("[login] response len="+str(len(r2.text)))

        log_cb("INFO","Checking internet...")
        time.sleep(2)
        if has_internet(settings):
            log_cb("OK","Login successful! Internet OK"); return True
        log_cb("WARN","Login done but internet not yet active"); return False

    except requests.RequestException as e:
        dbg("[login] RequestException:\n"+traceback.format_exc())
        log_cb("ERR","Network error: "+str(e)); return False
    except Exception as e:
        dbg("[login] Exception:\n"+traceback.format_exc())
        log_cb("ERR","Error: "+str(e)); return False

# ── read key ──────────────────────────────────────────────────────────────────
def read_key():
    with term.cbreak(): return term.inkey(timeout=None)

# ── WiFi popup ────────────────────────────────────────────────────────────────
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
        if key.code in (term.KEY_LEFT,term.KEY_TAB,term.KEY_BTAB):
            sel[0]=(sel[0]-1)%n_btn
        elif key.code==term.KEY_RIGHT:
            sel[0]=(sel[0]+1)%n_btn
        elif key.code==term.KEY_ENTER or ks in ("\n","\r"):
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

# ── Auto Login screen ─────────────────────────────────────────────────────────
LOG_COLORS={"OK":C_OK,"ERR":C_ERR,"WARN":C_WARN,"INFO":C_DIM,"DBG":C_DBG}
LOG_ICONS ={"OK":"\u2713","ERR":"\u2717","WARN":"\u26a0","INFO":"\u2022","DBG":"\u25c6"}
STATUS_COLORS={"ONLINE":C_OK,"OFFLINE":C_ERR,"LOGGING IN":C_WARN,"CHECKING":C_DIM}

def run_auto_login_screen(settings, bg_stop=None):
    scroll=[0]; spin_i=[0]; local_stop=threading.Event()

    def worker():
        chk=settings["check_interval"]; ret=settings["retry_interval"]
        while not local_stop.is_set():
            _set_status("CHECKING",notify=False)
            _add_log("INFO","Checking internet connection...")
            if has_internet(settings):
                _set_status("ONLINE")
                _add_log("OK","Internet OK - next check in "+str(chk)+"s")
                for _ in range(chk*2):
                    if local_stop.is_set(): return
                    time.sleep(0.5)
            else:
                _set_status("OFFLINE")
                _add_log("WARN","No internet, attempting login...")
                _set_status("LOGGING IN",notify=False)
                ok=do_login(settings,_add_log)
                if ok:
                    _set_status("ONLINE")
                    _add_log("OK","Connected! Next check in "+str(chk)+"s")
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
              C_DIM+" chk="+str(chk)+"s ret="+str(ret)+"s"+RST)
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
                elif key.code==term.KEY_UP:
                    with _log_lock: scroll[0]=max(0,scroll[0]-1)
                elif key.code==term.KEY_DOWN:
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
            _add_log("INFO","[BG] Checking connection...")
            if has_internet(settings):
                _set_status("ONLINE")
                _add_log("OK","[BG] Internet OK")
                for _ in range(chk*2):
                    if _bg_stop.is_set(): return
                    time.sleep(0.5)
            else:
                _set_status("OFFLINE")
                _add_log("WARN","[BG] No internet, logging in...")
                _set_status("LOGGING IN",notify=False)
                ok=do_login(settings,_add_log)
                if ok:
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

# ── Network test ─────────────────────────────────────────────────────────────
def ping_host(host="8.8.8.8", count=4):
    """Ping host and return (avg_ms, loss_pct) or (None, None) on error."""
    try:
        result = subprocess.run(
            ["ping","-n",str(count),host],
            capture_output=True, encoding="utf-8", errors="ignore",
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=15)
        out = result.stdout
        # Parse "Average = Xms"
        import re
        avg = re.search(r"Average = (\d+)ms", out)
        loss= re.search(r"\((\d+)% loss\)", out)
        avg_ms   = int(avg.group(1))  if avg  else None
        loss_pct = int(loss.group(1)) if loss else None
        return avg_ms, loss_pct
    except Exception as e:
        dbg("[ping] error: "+str(e))
        return None, None

def run_speedtest_threaded(result_holder):
    """Run speedtest in thread, store result in result_holder[0]."""
    try:
        st = _speedtest_lib.Speedtest(secure=True)
        result_holder[0] = {"phase": "Finding best server..."}
        st.get_best_server()
        srv = st.results.server
        result_holder[0] = {"phase": "Testing download...", "server": srv.get("name","?")+", "+srv.get("country","")}
        dl = st.download() / 1_000_000
        result_holder[0]["download"] = dl
        result_holder[0]["phase"] = "Testing upload..."
        ul = st.upload() / 1_000_000
        result_holder[0]["upload"] = ul
        result_holder[0]["ping"]   = st.results.ping
        result_holder[0]["phase"]  = "done"
    except Exception as e:
        result_holder[0] = {"phase": "error", "error": str(e)}

def network_test_screen(settings):
    result   = [{}]
    phase    = ["idle"]   # idle | running | done | error
    ping_r   = [None]     # (avg_ms, loss_pct)
    stop_ev  = threading.Event()

    def do_test():
        phase[0] = "running"
        # Ping truoc
        result[0] = {"phase": "Pinging 8.8.8.8..."}
        avg_ms, loss = ping_host("8.8.8.8", count=4)
        ping_r[0] = (avg_ms, loss)
        if not stop_ev.is_set():
            run_speedtest_threaded(result[0])
        phase[0] = "done"

    spin_i = [0]

    def build():
        W=term.width or 80; H=term.height or 24
        bw=min(70,W-4); bh=20; bx=(W-bw)//2; by=max(0,(H-bh)//2)
        rows=[""]*H

        rows[by]   = " "*bx + box_top(bw," NETWORK TEST ")
        rows[by+1] = " "*bx + box_row(bw, center_in(C_TITLE+bold(" Network Speed Test "),bw-2))
        rows[by+2] = " "*bx + box_mid(bw)

        ph = result[0].get("phase","") if result[0] else ""
        r  = by+3

        if phase[0] == "idle":
            rows[r] = " "*bx + box_row(bw, center_in(C_KEY+"Enter"+RST+" to start network test   "+C_KEY+"Q"+RST+" back",bw-2))
            r+=1
        elif phase[0] in ("running",):
            spin = SPIN[spin_i[0]%len(SPIN)]; spin_i[0]+=1
            rows[r] = " "*bx + box_row(bw, " "+C_WARN+spin+" "+ph+RST); r+=1

        # Ping result
        if ping_r[0] is not None:
            avg_ms, loss = ping_r[0]
            if avg_ms is not None:
                if   avg_ms < 30:  pc = C_OK
                elif avg_ms < 80:  pc = C_WARN
                else:              pc = C_ERR
                ping_str = pc+str(avg_ms)+"ms"+RST
                loss_str = (C_ERR if (loss or 0)>0 else C_OK)+str(loss or 0)+"%"+RST
            else:
                ping_str = C_ERR+"Timeout"+RST
                loss_str = C_ERR+"N/A"+RST
            rows[r] = " "*bx + box_row(bw, "  Ping (8.8.8.8) : "+ping_str+"   Loss: "+loss_str); r+=1

        # Server
        srv = result[0].get("server","")
        if srv:
            rows[r] = " "*bx + box_row(bw, "  Server         : "+C_DIM+srv+RST); r+=1

        # Download
        dl = result[0].get("download")
        if dl is not None:
            if   dl >= 50: dc = C_OK
            elif dl >= 10: dc = C_WARN
            else:          dc = C_ERR
            bar_w = 30
            filled = int(min(dl/100*bar_w, bar_w))
            bar = dc+"█"*filled+C_DIM+"░"*(bar_w-filled)+RST
            rows[r] = " "*bx + box_row(bw, "  Download       : "+dc+("%.1f"%dl)+" Mbps"+RST+"  "+bar); r+=1

        # Upload
        ul = result[0].get("upload")
        if ul is not None:
            if   ul >= 20: uc = C_OK
            elif ul >= 5:  uc = C_WARN
            else:          uc = C_ERR
            bar_w = 30
            filled = int(min(ul/100*bar_w, bar_w))
            bar = uc+"█"*filled+C_DIM+"░"*(bar_w-filled)+RST
            rows[r] = " "*bx + box_row(bw, "  Upload         : "+uc+("%.1f"%ul)+" Mbps"+RST+"  "+bar); r+=1

        # Error
        err = result[0].get("error")
        if err:
            rows[r] = " "*bx + box_row(bw, "  "+C_ERR+"Error: "+err+RST); r+=1

        # Done
        if phase[0]=="done" and result[0].get("phase")=="done":
            rows[r] = " "*bx + box_mid(bw); r+=1
            rows[r] = " "*bx + box_row(bw, center_in(C_OK+bold(" Complete! ")+RST,bw-2)); r+=1

        # Fill remaining rows with box_mid
        bot = by+bh-1
        for rr in range(r, bot):
            if rows[rr] == "":
                rows[rr] = " "*bx + box_mid(bw)

        # Hint
        if phase[0] == "idle":
            hint = C_KEY+"Enter"+RST+" start   "+C_KEY+"Q"+RST+" back"
        elif phase[0] == "running":
            hint = C_WARN+"Testing... please wait"+RST+"   "+C_KEY+"Q"+RST+" cancel"
        else:
            hint = C_KEY+"Enter"+RST+" retest   "+C_KEY+"Q"+RST+" back"
        rows[bot-1] = " "*bx + box_row(bw, " "+hint)
        rows[bot]   = " "*bx + box_bot(bw)
        return rows

    test_thread = [None]

    try:
        while True:
            render(build())
            with term.cbreak(): key=term.inkey(timeout=0.4)
            if key:
                ks=str(key).upper()
                if ks=="Q" or key.code==term.KEY_ESCAPE:
                    stop_ev.set(); break
                elif key.code==term.KEY_ENTER or ks in ("\n","\r"):
                    if phase[0] in ("idle","done","error"):
                        # Reset va chay lai
                        result[0]={};ping_r[0]=None;phase[0]="running";stop_ev.clear()
                        test_thread[0]=threading.Thread(target=do_test,daemon=True)
                        test_thread[0].start()
    finally:
        stop_ev.set()


# -- Check for updates ---------------------------------------------------------
def check_update_available():
    """Return (latest_ver, download_url) or (None, err_str) on failure."""
    try:
        api = "https://api.github.com/repos/" + GITHUB_REPO + "/releases/latest"
        req = urllib.request.Request(api, headers={"User-Agent": "AWING-AutoLogin/" + APP_VERSION})
        try:
            r = urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as he:
            if he.code == 404:
                return APP_VERSION, None
            raise
        data = json.loads(r.read().decode())
        latest = data.get("tag_name", "").lstrip("v")
        dl_url = None
        for asset in data.get("assets", []):
            if asset.get("name") in ("main.py", "app2.py"):
                dl_url = asset.get("browser_download_url")
                break
        if not dl_url:
            dl_url = ("https://raw.githubusercontent.com/" + GITHUB_REPO +
                      "/refs/tags/v" + latest + "/main.py")
        return latest, dl_url
    except Exception as e:
        return None, str(e)

def _ver_tuple(v):
    try: return tuple(int(x) for x in str(v).split("."))
    except Exception: return (0,)

def update_screen():
    state    = ["checking"]
    info     = [""]
    latest   = [None]
    dl_url   = [None]
    spin_i   = [0]
    progress = [0]

    def do_check():
        ver, url = check_update_available()
        if ver is None:
            state[0] = "error"; info[0] = str(url); return
        latest[0] = ver; dl_url[0] = url
        if _ver_tuple(ver) <= _ver_tuple(APP_VERSION):
            state[0] = "up_to_date"; info[0] = "v" + ver
        else:
            state[0] = "available"; info[0] = "v" + ver

    def do_download():
        state[0] = "downloading"; progress[0] = 0
        try:
            dest = os.path.abspath(sys.argv[0])
            tmp  = dest + ".update_tmp"
            req  = urllib.request.Request(dl_url[0], headers={"User-Agent": "AWING-AutoLogin/" + APP_VERSION})
            resp = urllib.request.urlopen(req, timeout=30)
            total = int(resp.headers.get("Content-Length") or 0)
            done  = 0
            with open(tmp, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk: break
                    f.write(chunk); done += len(chunk)
                    if total > 0: progress[0] = int(done * 100 / total)
            bak = dest + ".bak"
            if os.path.exists(bak):
                try: os.remove(bak)
                except Exception: pass
            os.rename(dest, bak)
            os.rename(tmp, dest)
            state[0] = "done"
        except Exception as e:
            if os.path.exists(tmp):
                try: os.remove(tmp)
                except Exception: pass
            state[0] = "error"; info[0] = str(e)

    threading.Thread(target=do_check, daemon=True).start()
    sel = [0]

    def build():
        W = term.width or 80; H = term.height or 24
        bw = min(62, W-4); bh = 14; bx = (W-bw)//2; by = (H-bh)//2
        rows = [""] * H
        st   = state[0]
        rows[by]   = " "*bx + box_top(bw, " CHECK FOR UPDATES ")
        rows[by+1] = " "*bx + box_row(bw, center_in(C_TITLE+bold(" AWING Auto Login "), bw-2))
        rows[by+2] = " "*bx + box_row(bw, center_in(C_DIM+"Current: v"+APP_VERSION+RST, bw-2))
        rows[by+3] = " "*bx + box_mid(bw)

        spin = SPIN[spin_i[0] % len(SPIN)]; spin_i[0] += 1

        if st == "checking":
            rows[by+4] = " "*bx + box_row(bw, center_in(C_WARN+spin+" Checking GitHub..."+RST, bw-2))
            rows[by+5] = " "*bx + box_mid(bw)
        elif st == "up_to_date":
            rows[by+4] = " "*bx + box_row(bw, center_in(C_OK+bold("✓ Already up to date")+RST, bw-2))
            rows[by+5] = " "*bx + box_row(bw, center_in(C_DIM+"Latest: "+info[0]+RST, bw-2))
        elif st == "available":
            rows[by+4] = " "*bx + box_row(bw, center_in(C_WARN+bold("⬆ Update available!")+RST, bw-2))
            rows[by+5] = " "*bx + box_row(bw, center_in(C_DIM+"Latest: "+info[0]+RST, bw-2))
        elif st == "downloading":
            bar_w  = bw - 14
            filled = int(progress[0] / 100 * bar_w)
            bar    = C_OK+"█"*filled+C_DIM+"░"*(bar_w-filled)+RST
            rows[by+4] = " "*bx + box_row(bw, " "+C_WARN+spin+" Downloading... "+str(progress[0])+"%"+RST)
            rows[by+5] = " "*bx + box_row(bw, " "+bar)
        elif st == "done":
            rows[by+4] = " "*bx + box_row(bw, center_in(C_OK+bold("✓ Update complete!")+RST, bw-2))
            rows[by+5] = " "*bx + box_row(bw, center_in(C_DIM+"Restart app to apply"+RST, bw-2))
        elif st == "error":
            rows[by+4] = " "*bx + box_row(bw, center_in(C_ERR+"✗ Error"+RST, bw-2))
            rows[by+5] = " "*bx + box_row(bw, " "+C_ERR+info[0][:bw-4]+RST)

        rows[by+6] = " "*bx + box_mid(bw)

        if st == "available":
            btn_up = " Update Now "; btn_cn = "  Cancel  "; gap = 2
            total_w = len(btn_up)+len(btn_cn)+gap
            bb = (bw-total_w)//2
            b0 = (C_SEL+btn_up+RST) if sel[0]==0 else (C_DIM+btn_up+RST)
            b1 = (C_SEL+btn_cn+RST) if sel[0]==1 else (C_DIM+btn_cn+RST)
            btns = " "*bb + b0 + " "*gap + b1
        elif st in ("up_to_date","done","error"):
            btn_ok = "    OK    "
            btns   = center_in(C_SEL+btn_ok+RST, bw-2)
        else:
            btns = center_in(C_DIM+"Please wait..."+RST, bw-2)
        rows[by+7] = " "*bx + box_row(bw, btns)
        rows[by+8] = " "*bx + box_mid(bw)

        if st == "available":
            hint = C_KEY+"Left/Right"+RST+" select   "+C_KEY+"Enter"+RST+" confirm   "+C_KEY+"Q"+RST+" back"
        else:
            hint = C_KEY+"Enter"+RST+" / "+C_KEY+"Q"+RST+" back"
        rows[by+9]  = " "*bx + box_row(bw, center_in(hint, bw-2))
        for rr in range(by+10, by+13):
            rows[rr] = " "*bx + box_mid(bw)
        rows[by+13] = " "*bx + box_bot(bw)
        return rows

    while True:
        render(build())
        st = state[0]
        with term.cbreak(): key = term.inkey(timeout=0.35)
        if not key: continue
        ks = str(key).upper()
        if st == "downloading": continue
        if st == "available":
            if key.code in (term.KEY_LEFT, term.KEY_RIGHT):
                sel[0] = 1 - sel[0]
            elif key.code == term.KEY_ENTER or ks in ("\n", "\r"):
                if sel[0] == 0:
                    threading.Thread(target=do_download, daemon=True).start()
                else:
                    return
            elif ks == "Q" or key.code == term.KEY_ESCAPE:
                return
        else:
            if key.code in (term.KEY_ENTER, term.KEY_ESCAPE) or ks in ("Q", "\n", "\r"):
                return

# ── User Guide (Help) ─────────────────────────────────────────────────────────
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
        "  " + C_KEY + "⎔  Network Test" + RST + "      Ping check + download/upload speed test.",
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
        if key.code == term.KEY_UP:
            scroll[0] = max(0, scroll[0] - 1)
        elif key.code == term.KEY_DOWN:
            scroll[0] = min(max_scroll, scroll[0] + 1)
        elif key.code == term.KEY_HOME:
            scroll[0] = 0
        elif key.code == term.KEY_END:
            scroll[0] = max_scroll
        elif str(key).upper() in ("Q", "\x1b") or key.code == term.KEY_ESCAPE:
            break

# ── Uninstall ─────────────────────────────────────────────────────────────────
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
            subprocess.Popen(["cmd.exe", "/c", cmd], creationflags=subprocess.CREATE_NO_WINDOW)
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
        if key.code in (term.KEY_LEFT, term.KEY_RIGHT):
            sel[0] = 1 - sel[0]
        elif key.code == term.KEY_ENTER or ks in ("\n", "\r"):
            return (sel[0] == 0)
        elif ks in ("Q", "\x1b") or key.code == term.KEY_ESCAPE:
            return False

# ── Main menu ───────────────────────────────────────────────────────────────────
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
        for i,(label,action) in enumerate(MENU_ITEMS):
            suffix=""
            if action=="tray" and tray_running: suffix=C_OK+" [running]"+RST
            content=(C_SEL+"  "+label+suffix+RST) if i==sel else (C_DIM+"  "+label+RST+suffix)
            rows[row+3+i]=" "*bx+box_row(bw,content)
        rows[row+3+len(MENU_ITEMS)]=" "*bx+box_bot(bw)
        hr=row+3+len(MENU_ITEMS)+1
        hint=C_KEY+"\u2191\u2193"+RST+" navigate   "+C_KEY+"Enter"+RST+" select   "+C_KEY+"Q"+RST+" quit"
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

# ── Settings screen ───────────────────────────────────────────────────────────
# ── Settings screen ───────────────────────────────────────────────────────────
def settings_screen(settings):
    sel = 0; n = len(SETTING_KEYS); msg = ""; editing = False; buf = ""

    def build():
        W = term.width or 80; H = term.height or 24
        bw = min(74, W - 4); bh = n + 7; bx = (W - bw) // 2
        rows = [""] * H
        rows[1] = " " * bx + box_top(bw, "SETTINGS")
        rows[2] = " " * bx + box_row(bw, bold("  #  ") + C_DIM + "Label".ljust(28) + "Value" + RST)
        rows[3] = " " * bx + sep_row(bw)
        for i, key in enumerate(SETTING_KEYS):
            label = SETTING_LABELS[key]; value = settings[key]; ir = 4 + i
            num = str(i + 1).ljust(3)
            if isinstance(value, bool):
                val_disp = (C_OK + bold("[ ON  ]") + RST) if value else (C_DIM + "[ OFF ]" + RST)
            else:
                val_disp = C_VAL + str(value) + RST
            if i == sel:
                vs = (C_WARN + buf + "█" + RST) if editing else val_disp
                content = C_SEL + " " + num + " " + label.ljust(28) + RST + " " + vs
            else:
                content = " " + C_DIM + num + RST + " " + label.ljust(28) + " " + val_disp
            rows[ir] = " " * bx + box_row(bw, content)
        sp = 4 + n
        rows[sp] = " " * bx + sep_row(bw)
        rows[sp + 1] = " " * bx + box_row(bw, (C_OK if msg.startswith("✓") else C_WARN) + msg + RST if msg else "")
        if editing:
            hint = C_KEY + "Enter" + RST + " confirm   " + C_KEY + "Esc" + RST + " cancel"
        else:
            cur_k = SETTING_KEYS[sel]
            if isinstance(settings[cur_k], bool):
                act = C_KEY + "Enter/Space" + RST + " toggle [ON/OFF]"
            else:
                act = C_KEY + "Enter" + RST + " edit"
            hint = (C_KEY + "↑↓" + RST + " move   " + act +
                    "   " + C_KEY + "R" + RST + " reset   " + C_KEY + "S" + RST + " save   " + C_KEY + "Q" + RST + " back")
        rows[sp + 2] = " " * bx + box_row(bw, hint)
        rows[sp + 3] = " " * bx + box_bot(bw)
        return rows

    while True:
        render(build())
        key = read_key(); msg = ""
        cur_k = SETTING_KEYS[sel]
        is_bool = isinstance(settings[cur_k], bool)
        if editing:
            if key.code == term.KEY_ESCAPE:
                editing = False; buf = ""
            elif key.code == term.KEY_ENTER or str(key) in ("\n", "\r"):
                if buf:
                    cur = settings[cur_k]
                    if isinstance(cur, int):
                        if buf.isdigit():
                            settings[cur_k] = int(buf); msg = "✓ Updated: " + str(settings[cur_k])
                        else:
                            msg = "⚠ Must be an integer"
                    else:
                        settings[cur_k] = buf; msg = "✓ Updated: " + SETTING_LABELS[cur_k]
                editing = False; buf = ""
            elif key.code == term.KEY_BACKSPACE or str(key) in ("\x7f", "\x08"):
                buf = buf[:-1]
            else:
                ch = str(key)
                if ch.isprintable(): buf += ch
        else:
            ks = str(key).upper()
            if key.code == term.KEY_UP:
                sel = (sel - 1) % n
            elif key.code == term.KEY_DOWN:
                sel = (sel + 1) % n
            elif is_bool and (key.code in (term.KEY_ENTER, term.KEY_LEFT, term.KEY_RIGHT) or str(key) in ("\n", "\r", " ")):
                settings[cur_k] = not settings[cur_k]
                st_txt = "ON" if settings[cur_k] else "OFF"
                msg = f"✓ {SETTING_LABELS[cur_k]} = {st_txt}"
            elif not is_bool and (key.code == term.KEY_ENTER or str(key) in ("\n", "\r")):
                editing = True; buf = str(settings[cur_k])
            elif ks == "R":
                for k in DEFAULT_SETTINGS: settings[k] = DEFAULT_SETTINGS[k]
                msg = "✓ Reset to defaults"
            elif ks == "S":
                msg = ("✓ Saved!" if save_settings(settings) else "⚠ Failed to save!")
            elif ks == "Q" or key.code == term.KEY_ESCAPE:
                break
    return settings

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if "--uninstall" in sys.argv:
        print("\n" + bold("AWING Auto Login - Uninstaller"))
        try:
            ans = input("Are you sure you want to completely uninstall? (y/N): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nCanceled.")
            return
        if ans in ("y", "yes"):
            perform_uninstall()
        else:
            print("Uninstall canceled.")
        return

    settings=load_settings()
    _notif_on[0] = bool(settings.get("notifications", False))
    _debug_on[0] = bool(settings.get("debug", False))

    # Cache HWND truoc khi enter alt screen
    _get_hwnd()

    enter_alt(); hide_cursor()
    start_tray()

    wifi_ok=check_wifi_popup(settings)
    if not wifi_ok:
        exit_alt(); show_cursor(); stop_tray()
        print(C_WARN+"Exited."+RST); return

    tray_running=False
    try:
        while True:
            if _tray_quit.is_set(): break

            if _tray_show.is_set():
                _tray_show.clear()
                show_console()
                run_auto_login_screen(settings, bg_stop=_bg_stop if tray_running else None)
                continue

            action=main_menu(settings,tray_running)

            if action=="auto":
                if tray_running: stop_bg_worker(); tray_running=False
                run_auto_login_screen(settings)

            elif action=="tray":
                if not tray_running:
                    start_bg_worker(settings); tray_running=True
                # An terminal xuong tray
                W=term.width or 80; H=term.height or 24
                rows=[""]*H
                rows[H//2]  =center_in(C_OK+bold(" Switching to background mode... ")+RST,W)
                rows[H//2+2]=center_in(C_DIM+"Hiding window in 1 second"+RST,W)
                render(rows)
                time.sleep(1)
                hide_console()

            elif action=="nettest":
                network_test_screen(settings)

            elif action=="update":
                update_screen()

            elif action=="help":
                help_screen()

            elif action=="settings":
                settings=settings_screen(settings)
                _notif_on[0]=bool(settings.get("notifications",False))
                _debug_on[0]=bool(settings.get("debug",False))

            elif action=="uninstall":
                if uninstall_screen():
                    perform_uninstall()
                    return

            elif action=="quit":
                break

    except KeyboardInterrupt: pass
    finally:
        stop_bg_worker(); stop_tray()
        exit_alt(); show_cursor()

if __name__=="__main__":
    main()
