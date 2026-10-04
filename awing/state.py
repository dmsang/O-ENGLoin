"""awing/state.py — Shared mutable state: logs, status, last login time."""
import threading, time
from .ui import C_DIM, RST
from .tray import tray_update, notify as tray_notify

MAX_LOGS         = 500
_logs            = []
_log_lock        = threading.Lock()
_status          = ["OFFLINE"]
_status_lock     = threading.Lock()
_last_login_time = [None]

def _add_log(level, msg):
    ts = time.strftime("%H:%M:%S")
    with _log_lock:
        _logs.append((ts, level, msg))
        if len(_logs) > MAX_LOGS: _logs.pop(0)

def _set_status(s, notify=True):
    from .tray import _notif_on
    with _status_lock:
        prev = _status[0]; _status[0] = s
    tray_update(s)
    if notify and s != prev:
        if s == "ONLINE" and prev in ("OFFLINE","LOGGING IN"):
            tray_notify("AWING Login", "\u2713 Internet connected!")
        elif s == "OFFLINE" and prev == "ONLINE":
            tray_notify("AWING Login", "\u26a0 Internet disconnected!")

def _get_status():
    with _status_lock: return _status[0]

def _last_login_str():
    t = _last_login_time[0]
    if t is None: return ""
    secs = int(time.time() - t)
    if secs < 60:   return C_DIM + " | Last login: " + str(secs) + "s ago" + RST
    mins = secs // 60
    if mins < 60:   return C_DIM + " | Last login: " + str(mins) + "m ago" + RST
    hours = mins // 60; rem = mins % 60
    if rem:         return C_DIM + " | Last login: " + str(hours) + "h " + str(rem) + "m ago" + RST
    return C_DIM + " | Last login: " + str(hours) + "h ago" + RST