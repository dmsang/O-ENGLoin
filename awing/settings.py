"""awing/settings.py — Load/save settings and constant definitions."""
import os, json

_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = os.path.join(_DIR, "settings.json")

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
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            s = dict(DEFAULT_SETTINGS); s.update(saved); return s
        except Exception: pass
    return dict(DEFAULT_SETTINGS)

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        return True
    except Exception: return False