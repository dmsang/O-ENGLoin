"""awing/tray.py — System tray (pystray + Pillow). Gracefully no-ops if unavailable."""
import threading

try:
    import pystray
    from PIL import Image, ImageDraw
    _TRAY_SUPPORTED = True
except Exception:
    pystray = None
    _TRAY_SUPPORTED = False

_ICON_COLORS = {
    "ONLINE":     (80, 200, 120),
    "OFFLINE":    (220, 80, 80),
    "LOGGING IN": (240, 180, 50),
    "CHECKING":   (100, 160, 220),
}

_tray_ref  = [None]
_tray_show = threading.Event()
_tray_quit = threading.Event()
_notif_on  = [False]

def make_tray_icon(status="OFFLINE"):
    if not _TRAY_SUPPORTED: return None
    color = _ICON_COLORS.get(status, (150, 150, 150))
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    d.ellipse([1, 1, 62, 62], fill=color + (255,))
    cx, cy = 32, 38
    for radius, width in [(22, 4), (14, 4), (6, 4)]:
        d.arc([cx-radius, cy-radius, cx+radius, cy+radius], 200, 340,
              fill=(255, 255, 255, 230), width=width)
    d.ellipse([cx-4, cy-4, cx+4, cy+4], fill=(255, 255, 255, 255))
    return img

def tray_update(status):
    icon = _tray_ref[0]
    if icon is None: return
    try: icon.icon = make_tray_icon(status); icon.title = "AWING - " + status
    except Exception: pass

def notify(title, msg):
    if not _notif_on[0]: return
    icon = _tray_ref[0]
    if icon:
        try: icon.notify(msg, title)
        except Exception: pass

def start_tray(on_open_cb, on_quit_cb):
    if not _TRAY_SUPPORTED: return
    def on_open(icon, item): on_open_cb()
    def on_quit(icon, item): on_quit_cb(); icon.stop()
    menu = pystray.Menu(
        pystray.MenuItem("Open window", on_open, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", on_quit),
    )
    icon = pystray.Icon("AWING", make_tray_icon("OFFLINE"), "AWING Login", menu)
    _tray_ref[0] = icon
    threading.Thread(target=icon.run, daemon=True).start()

def stop_tray():
    icon = _tray_ref[0]
    if icon:
        try: icon.stop()
        except Exception: pass