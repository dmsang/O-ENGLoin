"""awing/wifi.py — Cross-platform WiFi SSID detection and connection."""
import subprocess, time
from .compat import IS_WIN, NO_WIN

_ssid_cache = [None, 0.0]
SSID_TTL    = 10.0

def _dbg(msg):
    from .state import _add_log
    from .settings import load_settings
    # only log if debug mode on
    from awing import _debug_on
    if _debug_on[0]: _add_log("DBG", msg)

def _fetch_ssid():
    try:
        if IS_WIN:
            out = subprocess.check_output(
                ["netsh","wlan","show","interfaces"],
                encoding="utf-8", errors="ignore", **NO_WIN)
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("SSID") and "BSSID" not in line:
                    parts = line.split(":",1)
                    if len(parts)==2: return parts[1].strip()
        else:
            try:
                out = subprocess.check_output(
                    ["iwgetid","-r"], encoding="utf-8", errors="ignore", timeout=3)
                ssid = out.strip()
                if ssid: return ssid
            except Exception: pass
            try:
                out = subprocess.check_output(
                    ["nmcli","-t","-f","active,ssid","dev","wifi"],
                    encoding="utf-8", errors="ignore", timeout=3)
                for line in out.splitlines():
                    if line.startswith("yes:"):
                        return line[4:].strip()
            except Exception: pass
    except Exception: pass
    return None

def get_current_ssid(force=False):
    now = time.time()
    if force or (now - _ssid_cache[1]) >= SSID_TTL:
        _ssid_cache[0] = _fetch_ssid()
        _ssid_cache[1] = now
    return _ssid_cache[0]

def get_available_ssids():
    try:
        if IS_WIN:
            out = subprocess.check_output(
                ["netsh","wlan","show","networks","mode=bssid"],
                encoding="utf-8", errors="ignore", **NO_WIN)
            ssids=[]
            for line in out.splitlines():
                line=line.strip()
                if line.startswith("SSID") and "BSSID" not in line:
                    parts=line.split(":",1)
                    if len(parts)==2:
                        s=parts[1].strip()
                        if s: ssids.append(s)
            return ssids
        else:
            out = subprocess.check_output(
                ["nmcli","-t","-f","ssid","dev","wifi","list"],
                encoding="utf-8", errors="ignore", timeout=5)
            return [l.strip() for l in out.splitlines() if l.strip()]
    except Exception: return []

def connect_to_ssid(ssid):
    try:
        if IS_WIN:
            r = subprocess.run(
                ["netsh","wlan","connect","name="+ssid],
                encoding="utf-8", errors="ignore", capture_output=True,
                timeout=15, **NO_WIN)
        else:
            r = subprocess.run(
                ["nmcli","dev","wifi","connect",ssid],
                encoding="utf-8", errors="ignore", capture_output=True, timeout=20)
        return r.returncode==0
    except Exception: return False