"""awing/ui.py — Terminal, ANSI colours, box drawing, rendering helpers."""
import re, sys, unicodedata
from blessed import Terminal

sys.stdout.reconfigure(encoding="utf-8")
term = Terminal()

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

APP_VERSION  = "1.0.7"
GITHUB_REPO = "dmsang/O-ENGLoin"

LOGO = [
    " _____        _____ _   _  _____   _            _       ",
    "|  _  |      |  ___| \\ | ||  __ \\ | |          (_)      ",
    "| | | |______| |__ |  \\| || |  \\/ | |     ___   _ _ __  ",
    "| | | |______|  __|| . ` || | __  | |    / _ \\ | | '_ \\ ",
    "\\ \\_/ /      | |___| |\\  || |_\\ \\ | |___| (_) || | | | |",
    " \\___/       \\____/\\_| \\_/ \\____/ \\_____/\\___/ |_|_| |_|",
]
SPIN = ["\u280b","\u2819","\u2839","\u2838","\u283c","\u2834","\u2826","\u2827","\u2807","\u280f"]

# ── Screen rendering ───────────────────────────────────────────────────────────
def strip_ansi(s): return re.sub(r"\033\[[^m]*m","",s)
def str_width(s):
    plain = strip_ansi(s)
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in plain)

def hide_cursor(): sys.stdout.write("\033[?25l"); sys.stdout.flush()
def show_cursor(): sys.stdout.write("\033[?25h"); sys.stdout.flush()
def enter_alt():   sys.stdout.write("\033[?1049h\033[2J\033[H"); sys.stdout.flush()
def exit_alt():    sys.stdout.write("\033[?1049l"); sys.stdout.flush()

def render(rows: list):
    W = term.width or 80
    out = ["\033[?2026h", "\033[H"]
    for i, row in enumerate(rows):
        plain = strip_ansi(row)
        pad   = W - str_width(row)
        out.append(row + (" "*pad if pad > 0 else ""))
        if i < len(rows)-1:
            out.append("\n")
    out.append("\033[?2026l")
    sys.stdout.write("".join(out))
    sys.stdout.flush()

def center_in(text, width):
    plain = strip_ansi(text)
    pad   = max(0, width - str_width(text))
    return " "*(pad//2) + text

def box_top(w, title=""):
    inner = w-2
    if title:
        t = " "+title+" "; pad = inner-str_width(t)
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
    if str_width(content) > inner:
        target = inner-3; cur_w = 0; out = []; i = 0
        while i < len(content):
            if content[i] == "\033" and i+1 < len(content) and content[i+1] == "[":
                j = i+2
                while j < len(content) and content[j] not in "m": j += 1
                out.append(content[i:j+1]); i = j+1
            else:
                ch = content[i]
                ch_w = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
                if cur_w + ch_w <= target:
                    out.append(ch)
                    cur_w += ch_w
                i += 1
        content = "".join(out)+RST+"..."
    sw = str_width(content)
    padded = content+" "*max(0, inner-sw)
    return C_BORDER+"\u2502"+RST+padded+C_BORDER+"\u2502"+RST

def sep_row(w):
    return C_BORDER+"\u251c"+"\u2500"*(w-2)+"\u2524"+RST

# ── Mouse helpers ─────────────────────────────────────────────────────────────
def read_key():
    with term.cbreak(): return term.inkey(timeout=None)

def is_mouse_click(key):
    if key.code != term.KEY_MOUSE: return False
    name = key.mouse_event_name()
    return name is not None and "LEFT" in name and "RELEASED" not in name and "MOTION" not in name

def mouse_row(key):
    yx = key.mouse_yx; return yx[0] if yx else -1

def mouse_col(key):
    yx = key.mouse_yx; return yx[1] if yx else -1

def mouse_scroll_up(key):
    name = key.mouse_event_name() if key.code == term.KEY_MOUSE else None
    return name is not None and "SCROLL_UP" in name

def mouse_scroll_down(key):
    name = key.mouse_event_name() if key.code == term.KEY_MOUSE else None
    return name is not None and "SCROLL_DOWN" in name