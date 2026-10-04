"""awing — AWING Auto Login package."""
from .compat  import IS_WIN, IS_LINUX
from .ui      import (term, RST, bold, C_TITLE, C_BORDER, C_SEL, C_OK, C_ERR,
                      C_WARN, C_DIM, C_KEY, C_VAL, C_DBG, LOGO, APP_VERSION,
                      GITHUB_REPO, SPIN, render, center_in, box_top, box_mid,
                      box_bot, box_row, sep_row, strip_ansi, str_width, hide_cursor,
                      show_cursor, enter_alt, exit_alt,
                      read_key, is_mouse_click, mouse_row, mouse_col,
                      mouse_scroll_up, mouse_scroll_down)
from .settings import (SETTINGS_FILE, DEFAULT_SETTINGS, SETTING_LABELS,
                       SETTING_KEYS, load_settings, save_settings)
from .tray    import (_tray_ref, _tray_show, _tray_quit, _notif_on,
                      start_tray, stop_tray, _TRAY_SUPPORTED)
from .state   import (_logs, _log_lock, _status, _last_login_time,
                      _add_log, _set_status, _get_status, _last_login_str,
                      MAX_LOGS)
from .wifi    import (get_current_ssid, get_available_ssids, connect_to_ssid)
from .network import (has_internet, do_login, get_local_ip, ping_host,
                      run_speedtest_threaded)
from .compat  import hide_console, show_console, _get_hwnd

# Shared debug flag — modules read this via  from awing import _debug_on
_debug_on = [False]

def dbg(msg):
    if _debug_on[0]:
        _add_log("DBG", msg)

STATUS_COLORS = {"ONLINE": C_OK, "OFFLINE": C_ERR, "LOGGING IN": C_WARN, "CHECKING": C_DIM}
LOG_COLORS    = {"OK": C_OK, "ERR": C_ERR, "WARN": C_WARN, "INFO": C_DIM, "DBG": C_DBG}
LOG_ICONS     = {"OK": "\u2713", "ERR": "\u2717", "WARN": "\u26a0", "INFO": "\u2022", "DBG": "\u25c6"}