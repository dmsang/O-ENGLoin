"""awing/ui.py — Terminal, ANSI colours, themes, box drawing, rendering helpers."""
import re, sys, unicodedata
from blessed import Terminal

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
term = Terminal()

# ── ANSI Helpers ──────────────────────────────────────────────────────────────
RST = "\033[0m"
def fg(r, g, b): return f"\033[38;2;{r};{g};{b}m"
def bg(r, g, b): return f"\033[48;2;{r};{g};{b}m"
def bold(s):     return f"\033[1m{s}{RST}"

# ── Color Themes ──────────────────────────────────────────────────────────────
THEMES = {
    "ocean": {
        "name": "Ocean Blue",
        "title": fg(100, 200, 255),
        "border": fg(60, 100, 160),
        "sel": bg(30, 80, 160) + fg(255, 255, 255),
        "ok": fg(80, 200, 120),
        "err": fg(220, 80, 80),
        "warn": fg(240, 180, 50),
        "dim": fg(120, 120, 140),
        "key": fg(180, 220, 255),
        "val": fg(200, 230, 255),
        "dbg": fg(180, 120, 255),
    },
    "cyberpunk": {
        "name": "Cyberpunk Neon",
        "title": fg(255, 110, 180),
        "border": fg(140, 60, 200),
        "sel": bg(140, 20, 100) + fg(0, 255, 220),
        "ok": fg(0, 255, 180),
        "err": fg(255, 50, 90),
        "warn": fg(255, 220, 40),
        "dim": fg(150, 120, 170),
        "key": fg(0, 230, 255),
        "val": fg(255, 160, 220),
        "dbg": fg(255, 100, 255),
    },
    "matrix": {
        "name": "Matrix Terminal",
        "title": fg(80, 255, 120),
        "border": fg(30, 120, 50),
        "sel": bg(20, 90, 40) + fg(180, 255, 190),
        "ok": fg(50, 255, 100),
        "err": fg(255, 70, 70),
        "warn": fg(230, 230, 60),
        "dim": fg(80, 140, 90),
        "key": fg(140, 255, 160),
        "val": fg(180, 255, 200),
        "dbg": fg(100, 220, 150),
    },
    "dracula": {
        "name": "Dracula / Monokai",
        "title": fg(189, 147, 249),
        "border": fg(98, 114, 164),
        "sel": bg(68, 71, 90) + fg(241, 250, 140),
        "ok": fg(80, 250, 123),
        "err": fg(255, 85, 85),
        "warn": fg(255, 184, 108),
        "dim": fg(120, 130, 160),
        "key": fg(139, 233, 253),
        "val": fg(248, 248, 242),
        "dbg": fg(255, 121, 198),
    },
    "amber": {
        "name": "Sunset Amber",
        "title": fg(255, 180, 60),
        "border": fg(160, 100, 30),
        "sel": bg(140, 70, 20) + fg(255, 240, 180),
        "ok": fg(120, 210, 100),
        "err": fg(240, 80, 70),
        "warn": fg(255, 200, 70),
        "dim": fg(150, 130, 100),
        "key": fg(255, 210, 120),
        "val": fg(255, 230, 180),
        "dbg": fg(220, 140, 200),
    },
}

ACTIVE_THEME = ["ocean"]

class ColorProxy:
    def __init__(self, key):
        self.key = key
    def _val(self):
        theme = THEMES.get(ACTIVE_THEME[0], THEMES["ocean"])
        return theme.get(self.key, "")
    def __str__(self):
        return self._val()
    def __repr__(self):
        return self._val()
    def __add__(self, other):
        return self._val() + str(other)
    def __radd__(self, other):
        return str(other) + self._val()
    def __eq__(self, other):
        return self._val() == str(other)
    def __hash__(self):
        return hash(self._val())

def apply_theme(theme_name):
    if theme_name in THEMES:
        ACTIVE_THEME[0] = theme_name

C_TITLE  = ColorProxy("title")
C_BORDER = ColorProxy("border")
C_SEL    = ColorProxy("sel")
C_OK     = ColorProxy("ok")
C_ERR    = ColorProxy("err")
C_WARN   = ColorProxy("warn")
C_DIM    = ColorProxy("dim")
C_KEY    = ColorProxy("key")
C_VAL    = ColorProxy("val")
C_DBG    = ColorProxy("dbg")

APP_VERSION  = "1.0.9"
GITHUB_REPO = "dmsang/O-ENGLoin"

LOGO = [
    r" _____        _____ _   _  _____   _            _       ",
    r"|  _  |      |  ___| \ | ||  __ \ | |          (_)      ",
    r"| | | |______| |__ |  \| || |  \/ | |     ___   _ _ __  ",
    r"| | | |______|  __|| . ` || | __  | |    / _ \ | | '_ \ ",
    r"\ \_/ /      | |___| |\  || |_\ \ | |___| (_) || | | | |",
    r" \___/       \____/\_| \_/ \____/ \_____/\___/ |_|_| |_|",
]
SPIN = ["\u280b","\u2819","\u2839","\u2838","\u283c","\u2834","\u2826","\u2827","\u2807","\u280f"]

# ── Box Styles ────────────────────────────────────────────────────────────────
BOX_STYLES = {
    "rounded": {
        "tl": "╭", "tr": "╮", "bl": "╰", "br": "╯",
        "h": "─", "v": "│", "ml": "├", "mr": "┤"
    },
    "classic": {
        "tl": "┌", "tr": "┐", "bl": "└", "br": "┘",
        "h": "─", "v": "│", "ml": "├", "mr": "┤"
    },
    "double": {
        "tl": "╔", "tr": "╗", "bl": "╚", "br": "╝",
        "h": "═", "v": "║", "ml": "╠", "mr": "╣"
    }
}

ACTIVE_BOX_STYLE = ["rounded"]

def set_box_style(style_name):
    if style_name in BOX_STYLES:
        ACTIVE_BOX_STYLE[0] = style_name

# ── Screen rendering ───────────────────────────────────────────────────────────
def strip_ansi(s): return re.sub(r"\033\[[0-9;?]*[a-zA-Z]", "", str(s))
def str_width(s):
    plain = strip_ansi(s)
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in plain)

def hide_cursor(): sys.stdout.write("\033[?25l"); sys.stdout.flush()
def show_cursor(): sys.stdout.write("\033[?25h"); sys.stdout.flush()
def enter_alt():   sys.stdout.write("\033[?1049h\033[2J\033[H"); sys.stdout.flush()
def exit_alt():    sys.stdout.write("\033[?1049l"); sys.stdout.flush()

def render(rows: list):
    out = ["\033[?2026h", "\033[H"]
    for i, row in enumerate(rows):
        out.append(row + "\033[K")
        if i < len(rows) - 1:
            out.append("\n")
    out.append("\033[J\033[?2026l")
    sys.stdout.write("".join(out))
    sys.stdout.flush()

def center_in(text, width):
    plain = strip_ansi(text)
    pad   = max(0, width - str_width(text))
    return " " * (pad // 2) + text

def box_top(w, title=""):
    inner = w - 2
    bs = BOX_STYLES.get(ACTIVE_BOX_STYLE[0], BOX_STYLES["rounded"])
    if title:
        t = " " + title + " "
        pad = inner - str_width(t)
        top = bs["h"] * (pad // 2) + t + bs["h"] * (pad - pad // 2)
    else:
        top = bs["h"] * inner
    return C_BORDER + bs["tl"] + top + bs["tr"] + RST

def box_mid(w):
    bs = BOX_STYLES.get(ACTIVE_BOX_STYLE[0], BOX_STYLES["rounded"])
    return C_BORDER + bs["v"] + RST + " " * (w - 2) + C_BORDER + bs["v"] + RST

def box_bot(w):
    bs = BOX_STYLES.get(ACTIVE_BOX_STYLE[0], BOX_STYLES["rounded"])
    return C_BORDER + bs["bl"] + bs["h"] * (w - 2) + bs["br"] + RST

def sep_row(w):
    bs = BOX_STYLES.get(ACTIVE_BOX_STYLE[0], BOX_STYLES["rounded"])
    return C_BORDER + bs["ml"] + bs["h"] * (w - 2) + bs["mr"] + RST

def box_row(w, content):
    inner = w - 2
    bs = BOX_STYLES.get(ACTIVE_BOX_STYLE[0], BOX_STYLES["rounded"])
    v = bs["v"]
    if str_width(content) > inner:
        target = inner - 3; cur_w = 0; out = []; i = 0
        while i < len(content):
            if content[i] == "\033" and i + 1 < len(content) and content[i + 1] == "[":
                j = i + 2
                while j < len(content) and content[j] not in "m": j += 1
                out.append(content[i:j+1]); i = j + 1
            else:
                ch = content[i]
                ch_w = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
                if cur_w + ch_w <= target:
                    out.append(ch)
                    cur_w += ch_w
                i += 1
        content = "".join(out) + RST + "..."
    sw = str_width(content)
    padded = content + " " * max(0, inner - sw)
    return C_BORDER + v + RST + padded + C_BORDER + v + RST

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
