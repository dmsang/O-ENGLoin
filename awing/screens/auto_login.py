"""awing/screens/auto_login.py — Real-time auto-login screen and BG worker."""
import threading, time
from awing import (term, bold, C_TITLE, C_BORDER, C_SEL, C_OK, C_ERR, C_WARN,
                   C_DIM, C_KEY, C_VAL, C_DBG, RST, render, center_in,
                   box_top, box_mid, box_bot, box_row, sep_row,
                   is_mouse_click, mouse_scroll_up, mouse_scroll_down,
                   APP_VERSION, SPIN, STATUS_COLORS, LOG_COLORS, LOG_ICONS,
                   _debug_on, _tray_quit, _logs, _log_lock, _last_login_time,
                   _set_status, _get_status, _add_log, _last_login_str,
                   _get_remaining_sec, _format_remaining_tag, _update_session_remaining,
                   get_current_ssid, has_internet, do_login, get_gateway_status)

def dbg(msg):
    if _debug_on[0]: _add_log("DBG", msg)


def _auto_login_worker(settings, stop_event, is_bg=False):
    """Unified smart auto-login worker with countdown tracking and instant re-login."""
    chk = settings.get("check_interval", 15)
    ret = settings.get("retry_interval", 5)
    prefix = "[BG] " if is_bg else ""
    last_sync = [0.0]

    while not stop_event.is_set():
        now = time.time()
        rem = _get_remaining_sec()

        # 1. Periodically sync session time from router status page
        if (now - last_sync[0] >= 30) or (rem is None and _get_status() == "ONLINE"):
            st_data = get_gateway_status(settings, timeout=1.5)
            if "remaining_sec" in st_data:
                _update_session_remaining(st_data["remaining_sec"])
                rem = st_data["remaining_sec"]
                dbg(f"{prefix}Session lease synced: {rem}s ({st_data.get('remaining_str', '')})")
            last_sync[0] = now

        # 2. Instant auto-reconnect when session has just expired (rem <= 0)
        if rem is not None and rem <= 0:
            _set_status("LOGGING IN", notify=False)
            _add_log("INFO", f"{prefix}Session expired (0s) — instant auto-reconnect...")
            t0 = time.time()
            ok = do_login(settings, _add_log, max_retries=3)
            dur = time.time() - t0
            if ok:
                _last_login_time[0] = time.time()
                _set_status("ONLINE")
                _add_log("OK", f"{prefix}Reconnected in {dur:.1f}s! Session renewed.")
                st_data = get_gateway_status(settings, timeout=1.5)
                if "remaining_sec" in st_data:
                    _update_session_remaining(st_data["remaining_sec"])
                last_sync[0] = time.time()
                continue
            else:
                _set_status("OFFLINE")
                _add_log("ERR", f"{prefix}Instant re-login failed after retries — next cycle in {ret}s...")
                for _ in range(max(1, int(ret * 2))):
                    if stop_event.is_set(): return
                    time.sleep(0.5)
                continue

        # 3. Connectivity check
        _set_status("CHECKING", notify=False)
        dbg(f"{prefix}Checking connection...")
        online = has_internet(settings, timeout=1.5)

        if online:
            _set_status("ONLINE")
            rem = _get_remaining_sec()
            # Adaptive sleep: sleep longer when plenty of time, wake up fast right at cutoff
            if rem is not None:
                if rem > 20:
                    sleep_dur = min(chk, rem - 5)
                elif rem > 3:
                    sleep_dur = min(2.0, rem - 1)
                else:
                    sleep_dur = max(0.25, float(rem))
            else:
                sleep_dur = chk

            steps = max(1, int(sleep_dur * 2))
            for _ in range(steps):
                if stop_event.is_set(): return
                time.sleep(0.5)

        else:
            _set_status("OFFLINE")
            _add_log("WARN", f"{prefix}Internet lost — attempting login...")
            _set_status("LOGGING IN", notify=False)
            t0 = time.time()
            ok = do_login(settings, _add_log, max_retries=3)
            dur = time.time() - t0
            if ok:
                _last_login_time[0] = time.time()
                _set_status("ONLINE")
                _add_log("OK", f"{prefix}Reconnected in {dur:.1f}s!")
                st_data = get_gateway_status(settings, timeout=1.5)
                if "remaining_sec" in st_data:
                    _update_session_remaining(st_data["remaining_sec"])
                last_sync[0] = time.time()
                steps = max(1, chk * 2)
                for _ in range(steps):
                    if stop_event.is_set(): return
                    time.sleep(0.5)
            else:
                _set_status("OFFLINE")
                _add_log("ERR", f"{prefix}Login failed after retries — next cycle in {ret}s...")
                for _ in range(max(1, int(ret * 2))):
                    if stop_event.is_set(): return
                    time.sleep(0.5)


def run_auto_login_screen(settings, bg_stop=None):
    scroll = [0]; spin_i = [0]; local_stop = threading.Event()

    if bg_stop is None:
        wt = threading.Thread(target=lambda: _auto_login_worker(settings, local_stop, is_bg=False), daemon=True)
        wt.start()
    else:
        wt = None

    def build():
        W = term.width or 80; H = term.height or 24
        LOG_Y = 4
        st = _get_status(); sc = STATUS_COLORS.get(st, C_DIM)
        spin = SPIN[spin_i[0] % len(SPIN)]; spin_i[0] += 1
        gw = settings["gateway"]; chk = settings["check_interval"]; ret = settings["retry_interval"]
        ssid = get_current_ssid() or "(N/A)"
        req = settings.get("required_ssid", "")
        sc2 = C_OK if ssid == req else C_WARN
        dbg_tag = (" " + C_DBG + "[DEBUG]" + RST) if _debug_on[0] else ""

        LOG_H = max(1, H - 7)
        rows = [""] * max(H, LOG_Y + LOG_H + 3)
        rows[0] = box_top(W)
        rows[1] = box_row(W, center_in(C_TITLE + bold(" AWING Auto Login v" + APP_VERSION + " ") + dbg_tag, W - 2))

        rem_tag = _format_remaining_tag(compact=False, show_bar=True) if W >= 85 else _format_remaining_tag(compact=True)
        chk_info = C_DIM + " chk=" + str(chk) + "s" + RST if (W >= 95 or not rem_tag) else ""
        info = (" GW:" + C_VAL + gw + RST +
                " WiFi:" + sc2 + ssid + RST +
                " Status:" + sc + bold(st) + RST + sc + " " + spin + RST +
                rem_tag + chk_info + _last_login_str())
        rows[2] = box_row(W, info)
        rows[3] = sep_row(W)

        with _log_lock:
            total = len(_logs); start = scroll[0]
            visible = list(_logs[start:start+LOG_H])

        for i in range(LOG_H):
            if i < len(visible):
                ts, lvl, msg = visible[i]
                c = LOG_COLORS.get(lvl, C_DIM); ic = LOG_ICONS.get(lvl, " ")
                content = " " + C_DIM + ts + RST + " " + c + ic + " " + msg + RST
            else:
                content = ""
            rows[LOG_Y + i] = box_row(W, content)

        sep = LOG_Y + LOG_H
        rows[sep] = sep_row(W)

        is_bg = bg_stop is not None
        if total > LOG_H:
            sb = C_DIM + "(" + str(start + 1) + "-" + str(min(start + LOG_H, total)) + "/" + str(total) + ")" + RST
        else:
            sb = ""
        if is_bg:
            hint = (C_KEY + "\u2191\u2193" + RST + " scroll " + sb +
                    "  " + C_KEY + "End" + RST + " jump to bottom" +
                    "  " + C_KEY + "Q/Esc" + RST + " hide to tray" +
                    "  " + C_KEY + "X" + RST + " stop worker")
        else:
            hint = (C_KEY + "\u2191\u2193" + RST + " scroll " + sb +
                    "  " + C_KEY + "End" + RST + " jump to bottom" +
                    "  " + C_KEY + "Q/Esc" + RST + " back to menu")
        rows[sep + 1] = box_row(W, " " + hint)
        rows[sep + 2] = box_bot(W)
        return rows

    try:
        while True:
            if _tray_quit.is_set(): break
            render(build())
            with term.cbreak(): key = term.inkey(timeout=0.35)
            if key:
                ks = str(key).upper()
                if key.code == term.KEY_ESCAPE or ks == "Q": break
                elif ks == "X" and bg_stop is not None: bg_stop.set(); break
                elif key.code == term.KEY_UP or mouse_scroll_up(key):
                    with _log_lock: scroll[0] = max(0, scroll[0] - 1)
                elif key.code == term.KEY_DOWN or mouse_scroll_down(key):
                    with _log_lock:
                        _lh = (term.height or 24) - 7
                        total = len(_logs)
                        scroll[0] = min(max(0, total - _lh), scroll[0] + 1)
                elif key.code == term.KEY_END or ks == "G":
                    with _log_lock:
                        _lh = (term.height or 24) - 7
                        scroll[0] = max(0, len(_logs) - _lh)
                elif key.code == term.KEY_HOME:
                    scroll[0] = 0
    finally:
        local_stop.set()
        if wt: wt.join(timeout=2)


# ── Background worker ─────────────────────────────────────────────────────────
_bg_stop   = threading.Event()
_bg_thread = [None]

def start_bg_worker(settings):
    _bg_stop.clear()
    t = threading.Thread(target=lambda: _auto_login_worker(settings, _bg_stop, is_bg=True), daemon=True)
    t.start()
    _bg_thread[0] = t

def stop_bg_worker():
    _bg_stop.set()
    if _bg_thread[0]:
        _bg_thread[0].join(timeout=2)
