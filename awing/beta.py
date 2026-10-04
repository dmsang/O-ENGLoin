"""awing/beta.py — Beta features: pre-emptive re-login, ARP MAC bypass scanner."""
import re
import socket
import subprocess
import threading
import time

from .compat import IS_WIN, NO_WIN
from .state  import _add_log, _last_login_time

# ── Shared beta state ─────────────────────────────────────────────────────────
_beta_on       = [False]   # master beta toggle (read from settings)
_preempt_on    = [False]   # pre-emptive re-login toggle
_arp_on        = [False]   # ARP MAC spoof toggle
_arp_status    = ["idle"]  # "idle" | "scanning" | "spoofing:<MAC>" | "error:<msg>"
_original_mac  = [None]    # original MAC before spoof
_spoofed       = [False]   # is currently spoofed?

# ── Helpers ──────────────────────────────────────────────────────────────────
def _dbg(msg):
    from awing import _debug_on
    if _debug_on[0]:
        _add_log("DBG", "[beta] " + msg)


def _run(cmd, timeout=8):
    """Run a subprocess silently, return stdout string or '' on error."""
    try:
        r = subprocess.run(
            cmd, capture_output=True,
            encoding="utf-8", errors="ignore",
            timeout=timeout, **NO_WIN)
        return r.stdout
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
#  FEATURE 1 — Pre-emptive re-login (seamless session renewal)
# ─────────────────────────────────────────────────────────────────────────────
def preempt_window(settings):
    """Seconds before session expiry to trigger pre-emptive login.
    Re-logs in at (session_duration - window) seconds after last login."""
    return settings.get("beta_preempt_window", 30)   # default 30 s before cutoff


def should_preempt(settings):
    """Return True if pre-emptive re-login should fire right now."""
    if not (_beta_on[0] and _preempt_on[0]):
        return False
    last = _last_login_time[0]
    if not last:
        return False
    session_len = settings.get("beta_session_len", 900)   # default 15 min
    window      = preempt_window(settings)
    elapsed     = time.time() - last
    # Fire when there are `window` seconds left in the session
    return elapsed >= (session_len - window)


# ─────────────────────────────────────────────────────────────────────────────
#  FEATURE 2 — ARP Scanner: find bypass MACs + spoof
# ─────────────────────────────────────────────────────────────────────────────

def _is_valid_candidate_ip(ip, mac, gateway):
    if not ip or not mac or ip == gateway:
        return False
    mac_up = mac.upper()
    if mac_up.startswith("01:00:5E") or mac_up.startswith("33:33") or mac_up in ("FF:FF:FF:FF:FF:FF", "00:00:00:00:00:00"):
        return False
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        first, last = int(parts[0]), int(parts[3])
    except ValueError:
        return False
    if first >= 224 or first == 0 or first == 127:
        return False
    if last in (0, 255):
        return False
    gw_prefix = ".".join(gateway.split(".")[:2])
    if not ip.startswith(gw_prefix):
        return False
    return True


def _get_arp_table(gateway):
    """Return list of (ip, mac) tuples from the ARP cache."""
    entries = []
    seen = set()
    if IS_WIN:
        out = _run(["arp", "-a"])
        blocks = re.split(r"\n(?=Interface:)", out)
        target_text = out
        for b in blocks:
            if gateway in b:
                target_text = b
                break
        for line in target_text.splitlines():
            m = re.search(
                r"(\d{1,3}(?:\.\d{1,3}){3})\s+([\da-fA-F]{2}[-:][\da-fA-F]{2}"
                r"[-:][\da-fA-F]{2}[-:][\da-fA-F]{2}[-:][\da-fA-F]{2}[-:][\da-fA-F]{2})\s+(\w+)",
                line)
            if m:
                ip = m.group(1)
                mac = m.group(2).replace("-", ":").upper()
                kind = m.group(3).lower()
                if kind in ("dynamic", "static") and _is_valid_candidate_ip(ip, mac, gateway):
                    if ip not in seen:
                        seen.add(ip)
                        entries.append((ip, mac))
    else:
        out = _run(["arp", "-n"])
        for line in out.splitlines():
            m = re.search(
                r"(\d{1,3}(?:\.\d{1,3}){3})\s+\w+\s+([\da-fA-F]{2}:[\da-fA-F]{2}"
                r":[\da-fA-F]{2}:[\da-fA-F]{2}:[\da-fA-F]{2}:[\da-fA-F]{2})",
                line)
            if m:
                ip, mac = m.group(1), m.group(2).upper()
                if _is_valid_candidate_ip(ip, mac, gateway):
                    if ip not in seen:
                        seen.add(ip)
                        entries.append((ip, mac))
    return entries


def _get_wifi_guid_win():
    out = _run(["netsh", "wlan", "show", "interfaces"])
    m = re.search(r"GUID\s*:\s*([a-fA-F0-9\-]+)", out)
    return m.group(1).strip("{}").lower() if m else None


def _get_own_mac_win():
    """Get current MAC of the active Wi-Fi adapter on Windows."""
    out = _run(["netsh", "wlan", "show", "interfaces"])
    m = re.search(r"Physical address\s*:\s*([\da-fA-F]{2}(?:[-:][\da-fA-F]{2}){5})", out, re.I)
    if m:
        return m.group(1).replace("-", ":").upper()
    return None


def _get_wifi_adapter_win():
    """Return the name of the active Wi-Fi adapter."""
    out = _run(["netsh", "wlan", "show", "interfaces"])
    m = re.search(r"^\s*Name\s*:\s*(.+)$", out, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None


def _ping_sweep(gateway, count=20, stop_event=None):
    """Quick ping sweep of the first `count` IPs in the subnet to populate ARP."""
    subnet = ".".join(gateway.split(".")[:3])
    threads = []
    for i in range(1, count + 1):
        if stop_event and stop_event.is_set():
            break
        ip = f"{subnet}.{i}"
        cmd = ["ping", "-n", "1", "-w", "200", ip] if IS_WIN else ["ping", "-c", "1", "-W", "1", ip]
        t = threading.Thread(target=lambda c=cmd: _run(c, timeout=2), daemon=True)
        t.start(); threads.append(t)
    for t in threads:
        if stop_event and stop_event.is_set():
            break
        t.join(timeout=2.5)


def _uptime_score(ip, gateway):
    """Ping `ip` 2 times; return response ratio 0.0-1.0 (higher = more stable)."""
    try:
        cmd = ["ping", "-n", "2", "-w", "250", ip] if IS_WIN else ["ping", "-c", "2", "-W", "1", ip]
        out = _run(cmd, timeout=3)
        ttl_matches = re.findall(r"ttl[=<]?\s*\d+", out, re.I)
        if ttl_matches:
            return min(1.0, len(ttl_matches) / 2.0)
        loss_m = re.search(r"\(\s*(\d+)%", out)
        if loss_m:
            loss = int(loss_m.group(1))
            return max(0.0, 1.0 - loss / 100.0)
        times = re.findall(r"(?:time|thời gian)[=<](\d+)ms", out, re.I)
        return 0.5 if times else 0.0
    except Exception:
        return 0.0


def scan_bypass_candidates(settings, progress_cb=None, stop_event=None):
    """
    Scan the local subnet for devices that are always online (likely bypass devices).
    Returns list of dicts: [{"ip":..., "mac":..., "score":..., "vendor":...}]
    sorted by score descending.
    """
    gateway = settings.get("gateway", "192.168.200.1")
    own_mac = _get_own_mac_win() if IS_WIN else None

    if stop_event and stop_event.is_set(): return []
    if progress_cb: progress_cb("Pinging subnet to build ARP table...")
    _ping_sweep(gateway, count=20, stop_event=stop_event)
    if stop_event and stop_event.is_set(): return []
    time.sleep(0.3)

    if stop_event and stop_event.is_set(): return []
    if progress_cb: progress_cb("Reading ARP table...")
    entries = _get_arp_table(gateway)
    _dbg(f"ARP valid entries: {len(entries)}")

    candidates = []
    total = len(entries)
    for idx, (ip, mac) in enumerate(entries):
        if stop_event and stop_event.is_set():
            _dbg("Scan stopped by user")
            break
        if progress_cb:
            progress_cb(f"Probing {idx+1}/{total}: {ip} ({mac[:8]}...)")
        if own_mac and mac == own_mac:
            continue
        score = _uptime_score(ip, gateway)
        oui = mac[:8].upper()
        vendor = _OUI_HINTS.get(oui, "Unknown")
        _dbg(f"{ip} {mac} score={score:.1f} vendor={vendor}")
        # If device replied to ping, score is 0.5-1.0; if present in dynamic ARP without ping response, score 0.3
        final_score = score if score > 0 else 0.3
        candidates.append({"ip": ip, "mac": mac, "score": final_score, "vendor": vendor})

    candidates.sort(key=lambda x: -x["score"])
    return candidates


# Common OUI prefixes for typical "always-on" devices
_OUI_HINTS = {
    # Cameras / NVR
    "48:EA:63": "Hikvision Camera",
    "BC:AD:28": "Hikvision Camera",
    "8C:E7:48": "Dahua Camera",
    "E0:50:8B": "Dahua Camera",
    "00:0F:FC": "TP-Link (AP/Switch)",
    "50:3E:AA": "TP-Link",
    "B0:95:75": "TP-Link",
    "EC:08:6B": "TP-Link",
    "94:D9:B3": "TP-Link",
    "C0:4A:00": "TP-Link",
    # POS / Payment terminals
    "00:17:88": "Philips Hue / IoT",
    "AC:CF:85": "POS Terminal",
    "00:1B:44": "SunRay POS",
    # Printers
    "00:00:48": "Epson Printer",
    "00:26:AB": "Epson Printer",
    "1C:C1:DE": "Canon Printer",
    "00:1E:8F": "Canon",
    "28:80:23": "HP Printer",
    "3C:D9:2B": "HP",
    "AC:E2:D3": "HP",
    "78:AC:C0": "Samsung Printer",
    # Smart TV / STB
    "8C:79:67": "Samsung SmartTV",
    "CC:6D:A0": "LG SmartTV",
    "00:1A:35": "LG",
    "A4:C3:F0": "Samsung",
    "40:B0:76": "Samsung",
    # Routers / AP (internal management)
    "00:0C:42": "MikroTik",
    "D4:CA:6D": "MikroTik",
    "B8:69:F4": "MikroTik",
    "4C:5E:0C": "MikroTik",
    "48:8F:5A": "Ubiquiti",
    "00:27:22": "Ubiquiti",
    "DC:9F:DB": "Ubiquiti",
}


# ── MAC Spoof ─────────────────────────────────────────────────────────────────

def _find_win_adapter_sub(class_key, adapter_name, write=False):
    import winreg
    guid = _get_wifi_guid_win()
    access = (winreg.KEY_READ | winreg.KEY_WRITE) if write else winreg.KEY_READ
    for i in range(256):
        subkey_name = f"{i:04d}"
        try:
            sub = winreg.OpenKey(class_key, subkey_name, 0, access)
        except OSError:
            try:
                sub = winreg.OpenKey(class_key, subkey_name, 0, winreg.KEY_READ)
            except OSError:
                break
        try:
            # 1. Match GUID
            if guid:
                try:
                    inst_guid, _ = winreg.QueryValueEx(sub, "NetCfgInstanceId")
                    if inst_guid.strip("{}").lower() == guid.strip("{}").lower():
                        return sub
                except OSError:
                    pass
            # 2. Match Connection Name
            try:
                inst_guid, _ = winreg.QueryValueEx(sub, "NetCfgInstanceId")
                net_path = fr"SYSTEM\CurrentControlSet\Control\Network\{{4D36E972-E325-11CE-BFC1-08002BE10318}}\{inst_guid}\Connection"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, net_path) as nk:
                    conn_name, _ = winreg.QueryValueEx(nk, "Name")
                    if conn_name.lower() == adapter_name.lower():
                        return sub
            except Exception:
                pass
            # 3. Match DriverDesc
            try:
                desc, _ = winreg.QueryValueEx(sub, "DriverDesc")
                if adapter_name.lower() in desc.lower():
                    return sub
            except OSError:
                pass
            winreg.CloseKey(sub)
        except Exception:
            winreg.CloseKey(sub)
    return None


def spoof_mac_win(adapter, new_mac):
    """
    Change MAC on Windows via registry + netsh.
    Requires the adapter to support MAC spoofing (most do).
    Returns True on success.
    """
    import winreg  # type: ignore
    try:
        base = r"SYSTEM\CurrentControlSet\Control\Class\{4D36E972-E325-11CE-BFC1-08002BE10318}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as class_key:
            sub = _find_win_adapter_sub(class_key, adapter, write=True)
            if sub:
                mac_str = new_mac.replace(":", "").upper()
                winreg.SetValueEx(sub, "NetworkAddress", 0, winreg.REG_SZ, mac_str)
                winreg.CloseKey(sub)
                _run(["netsh", "interface", "set", "interface", adapter, "admin=disable"], timeout=10)
                time.sleep(1)
                _run(["netsh", "interface", "set", "interface", adapter, "admin=enable"], timeout=10)
                time.sleep(2)
                return True
    except Exception as e:
        _dbg(f"spoof_mac_win error: {e}")
    return False


def spoof_mac_linux(iface, new_mac):
    """Change MAC on Linux via ip link. Returns True on success."""
    try:
        r1 = subprocess.run(["ip", "link", "set", iface, "down"],
                            capture_output=True, timeout=5)
        r2 = subprocess.run(["ip", "link", "set", iface, "address", new_mac],
                            capture_output=True, timeout=5)
        r3 = subprocess.run(["ip", "link", "set", iface, "up"],
                            capture_output=True, timeout=5)
        return r2.returncode == 0
    except Exception:
        return False


def restore_mac(adapter_or_iface):
    """Restore the original MAC if we saved one."""
    orig = _original_mac[0]
    if not orig:
        return False
    if IS_WIN:
        import winreg
        try:
            base = r"SYSTEM\CurrentControlSet\Control\Class\{4D36E972-E325-11CE-BFC1-08002BE10318}"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as class_key:
                sub = _find_win_adapter_sub(class_key, adapter_or_iface, write=True)
                if sub:
                    try:
                        winreg.DeleteValue(sub, "NetworkAddress")
                    except OSError:
                        pass
                    winreg.CloseKey(sub)
                    _run(["netsh", "interface", "set", "interface", adapter_or_iface, "admin=disable"], timeout=10)
                    time.sleep(1)
                    _run(["netsh", "interface", "set", "interface", adapter_or_iface, "admin=enable"], timeout=10)
                    time.sleep(2)
                    _spoofed[0] = False
                    _arp_status[0] = "idle"
                    _original_mac[0] = None
                    return True
        except Exception as e:
            _dbg(f"restore_mac error: {e}")
        ok = spoof_mac_win(adapter_or_iface, orig)
    else:
        ok = spoof_mac_linux(adapter_or_iface, orig)
    if ok:
        _spoofed[0] = False
        _arp_status[0] = "idle"
        _original_mac[0] = None
    return ok
