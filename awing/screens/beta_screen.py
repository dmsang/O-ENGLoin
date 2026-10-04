"""awing/screens/beta_screen.py — Beta Features management screen."""
import threading
import time

from awing import (IS_WIN, term, bold, C_TITLE, C_BORDER, C_SEL, C_OK, C_WARN,
                   C_ERR, C_DIM, C_KEY, C_VAL, C_DBG, RST, render, center_in,
                   box_top, box_mid, box_bot, box_row, sep_row,
                   read_key, is_mouse_click, mouse_row,
                   mouse_scroll_up, mouse_scroll_down,
                   save_settings)
from awing.beta import (
    _beta_on, _preempt_on, _arp_on, _arp_status,
    _original_mac, _spoofed,
    scan_bypass_candidates, spoof_mac_win, spoof_mac_linux,
    restore_mac, _get_wifi_adapter_win, _get_own_mac_win,
    should_preempt,
)


def beta_screen(settings):
    """Main beta features screen with sub-navigation."""
    sel = [0]
    msg = [""]
    scan_result  = [None]   # list of candidate dicts after scan
    scan_state   = ["idle"] # "idle"|"scanning"|"done"|"error"
    scan_prog    = [""]
    spoof_sel    = [0]      # selected candidate index for spoofing
    view         = ["menu"] # "menu" | "scan" | "spoof_confirm"

    ITEMS = [
        ("beta_enabled",   "\u26a1 Beta Features",          "master"),
        ("beta_preempt",   "\u23f1  Pre-emptive Re-login",  "preempt"),
        ("beta_arp",       "\ud83d\udcf6  ARP MAC Bypass",  "arp"),
    ]
    # sync toggles from settings
    _beta_on[0]    = bool(settings.get("beta_enabled", False))
    _preempt_on[0] = bool(settings.get("beta_preempt", False))
    _arp_on[0]     = bool(settings.get("beta_arp", False))

    def _save():
        settings["beta_enabled"] = _beta_on[0]
        settings["beta_preempt"] = _preempt_on[0]
        settings["beta_arp"]     = _arp_on[0]
        save_settings(settings)

    def _toggle(key):
        if key == "master":
            _beta_on[0] = not _beta_on[0]
            settings["beta_enabled"] = _beta_on[0]
        elif key == "preempt":
            if not _beta_on[0]: msg[0] = "\u26a0 Enable Beta Features first"; return
            _preempt_on[0] = not _preempt_on[0]
            settings["beta_preempt"] = _preempt_on[0]
        elif key == "arp":
            if not _beta_on[0]: msg[0] = "\u26a0 Enable Beta Features first"; return
            _arp_on[0] = not _arp_on[0]
            settings["beta_arp"] = _arp_on[0]
        _save()

    def _val(key):
        if key == "master":  return _beta_on[0]
        if key == "preempt": return _preempt_on[0]
        if key == "arp":     return _arp_on[0]
        return False

    def _build_menu():
        W = term.width or 80; H = max(term.height or 24, 24)
        rows = [""] * H
        bw = min(72, W - 4); bx = (W - bw) // 2

        rows[1] = " " * bx + box_top(bw, " \u26a1 BETA FEATURES ")
        rows[2] = " " * bx + box_row(bw, center_in(
            C_WARN + bold(" Experimental — may not work on all networks ") + RST, bw - 2))
        rows[3] = " " * bx + sep_row(bw)

        # Feature toggles
        for idx, (skey, label, fkey) in enumerate(ITEMS):
            val = _val(fkey)
            tog = (C_OK + bold("[ ON  ]") + RST) if val else (C_DIM + "[ OFF ]" + RST)
            dim = "" if (fkey == "master" or _beta_on[0]) else C_DIM
            if idx == sel[0]:
                content = C_SEL + "  " + label.ljust(30) + RST + " " + tog
            else:
                content = "  " + dim + label.ljust(30) + RST + " " + tog
            rows[4 + idx] = " " * bx + box_row(bw, content)

        rows[4 + len(ITEMS)] = " " * bx + sep_row(bw)

        # Description panel for selected item
        desc_row = 5 + len(ITEMS)
        descs = {
            "master": [
                C_DIM + "Master switch for all beta features." + RST,
                C_DIM + "Individual features remain inactive unless this is ON." + RST,
            ],
            "preempt": [
                C_OK + "\u23f1 Pre-emptive Re-login" + RST + C_DIM + " — logs in BEFORE session expires." + RST,
                C_DIM + "Default: re-login 30s before cutoff (configurable in Settings)." + RST,
                C_DIM + "Result: zero internet interruption during session renewal." + RST,
            ],
            "arp": [
                C_OK + "\ud83d\udcf6 ARP MAC Bypass" + RST + C_DIM + " — spoof MAC of a bypass device." + RST,
                C_DIM + "Scans subnet for always-online devices (POS, Camera, TV...)." + RST,
                C_DIM + "If a matching device is found, spoofs its MAC so router grants" + RST,
                C_DIM + "permanent access without the 15-min captive portal restriction." + RST,
                C_WARN + "\u26a0 Requires Admin/root. Press S to start ARP scan." + RST,
            ],
        }
        _, _, fkey = ITEMS[sel[0]]
        for i, dline in enumerate(descs.get(fkey, [])):
            r = desc_row + i
            if r < H - 4:
                rows[r] = " " * bx + box_row(bw, "  " + dline)

        # ARP status
        arps = _arp_status[0]
        if arps != "idle":
            ars_row = desc_row + 6
            if ars_row < H - 4:
                if arps.startswith("spoofing:"):
                    rows[ars_row] = " " * bx + box_row(bw, "  " + C_OK + "\u2713 Spoofed as: " + arps[9:] + RST)
                elif arps.startswith("error:"):
                    rows[ars_row] = " " * bx + box_row(bw, "  " + C_ERR + "\u2717 " + arps[6:] + RST)
                elif arps == "scanning":
                    rows[ars_row] = " " * bx + box_row(bw, "  " + C_WARN + "\u29d7 Scanning... " + scan_prog[0] + RST)

        # message bar
        msg_r = H - 3
        if msg[0]:
            clr = C_OK if msg[0].startswith("\u2713") else C_WARN
            rows[msg_r] = " " * bx + box_row(bw, clr + msg[0] + RST)

        # hints
        hint = (C_KEY + "\u2191\u2193" + RST + " move   " +
                C_KEY + "Enter/Space" + RST + " toggle   " +
                C_KEY + "S" + RST + " ARP scan   " +
                C_KEY + "R" + RST + " restore MAC   " +
                C_KEY + "Q" + RST + " back")
        rows[H - 2] = " " * bx + box_row(bw, " " + hint)
        rows[H - 1] = " " * bx + box_bot(bw)
        return rows

    def _build_scan():
        """ARP scan results screen."""
        W = term.width or 80; H = max(term.height or 24, 24)
        rows = [""] * H
        bw = min(72, W - 4); bx = (W - bw) // 2

        rows[1] = " " * bx + box_top(bw, " \ud83d\udcf6 ARP SCAN RESULTS ")
        if scan_state[0] == "scanning":
            rows[2] = " " * bx + box_row(bw, center_in(C_WARN + bold("\u29d7 Scanning... " + scan_prog[0]) + RST, bw - 2))
            rows[3] = " " * bx + sep_row(bw)
            rows[4] = " " * bx + box_row(bw, C_DIM + "  Pinging subnet, reading ARP, measuring uptime..." + RST)
            rows[H - 1] = " " * bx + box_bot(bw)
            return rows

        results = scan_result[0] or []
        rows[2] = " " * bx + box_row(bw, center_in(
            C_OK + bold(f"  Found {len(results)} candidate(s)  ") + RST, bw - 2))
        rows[3] = " " * bx + sep_row(bw)

        col_h = " #  " + "IP".ljust(17) + "MAC".ljust(20) + "Score".ljust(8) + "Vendor"
        rows[4] = " " * bx + box_row(bw, C_KEY + col_h + RST)
        rows[5] = " " * bx + sep_row(bw)

        max_show = H - 10
        for i, c in enumerate(results[:max_show]):
            score_bar = int(c["score"] * 5) * "\u2588" + (5 - int(c["score"] * 5)) * "\u2591"
            score_clr = C_OK if c["score"] > 0.8 else C_WARN
            line = (f" {i+1:<3}" +
                    c["ip"].ljust(17) +
                    c["mac"].ljust(20) +
                    score_clr + score_bar + RST + "  " +
                    C_DIM + c["vendor"] + RST)
            if i == spoof_sel[0]:
                rows[6 + i] = " " * bx + box_row(bw, C_SEL + "  " + line + RST)
            else:
                rows[6 + i] = " " * bx + box_row(bw, line)

        sep_r = 6 + min(len(results), max_show)
        rows[sep_r] = " " * bx + sep_row(bw)
        hint = (C_KEY + "\u2191\u2193" + RST + " select   " +
                C_KEY + "Enter" + RST + " spoof this MAC   " +
                C_KEY + "Q/Esc" + RST + " back")
        rows[sep_r + 1] = " " * bx + box_row(bw, " " + hint)
        rows[H - 1] = " " * bx + box_bot(bw)
        return rows

    def _do_scan():
        scan_state[0] = "scanning"
        _arp_status[0] = "scanning"

        def progress(txt):
            scan_prog[0] = txt

        try:
            results = scan_bypass_candidates(settings, progress_cb=progress)
            scan_result[0] = results
            scan_state[0] = "done"
            _arp_status[0] = "idle"
            spoof_sel[0] = 0
        except Exception as e:
            scan_state[0] = "error"
            _arp_status[0] = "error:" + str(e)

    def _do_spoof(candidate):
        mac = candidate["mac"]
        if IS_WIN:
            adapter = _get_wifi_adapter_win()
            if not adapter:
                _arp_status[0] = "error:Cannot detect WiFi adapter"
                return
            orig = _get_own_mac_win()
            _original_mac[0] = orig
            _arp_status[0] = "scanning"
            ok = spoof_mac_win(adapter, mac)
        else:
            # Linux: get interface from iw dev
            try:
                import subprocess as _sp
                out = _sp.check_output(["iw", "dev"], encoding="utf-8", timeout=3)
                m = __import__("re").search(r"Interface\s+(\S+)", out)
                iface = m.group(1) if m else "wlan0"
            except Exception:
                iface = "wlan0"
            _original_mac[0] = None
            ok = spoof_mac_linux(iface, mac)

        if ok:
            _spoofed[0] = True
            _arp_status[0] = "spoofing:" + mac
            msg[0] = "\u2713 MAC spoofed to " + mac + " — reconnecting..."
        else:
            _arp_status[0] = "error:Spoof failed (run as admin?)"
            msg[0] = "\u26a0 Spoof failed — try running as Administrator"

    # ── Event loop ────────────────────────────────────────────────────────────
    while True:
        if view[0] == "scan":
            render(_build_scan())
        else:
            render(_build_menu())

        key = read_key()
        n = len(ITEMS)
        ks = str(key).upper()

        if view[0] == "scan":
            results = scan_result[0] or []
            if scan_state[0] == "scanning":
                # Just wait, re-render
                time.sleep(0.3)
                continue
            if key.code == term.KEY_UP or mouse_scroll_up(key):
                spoof_sel[0] = max(0, spoof_sel[0] - 1)
            elif key.code == term.KEY_DOWN or mouse_scroll_down(key):
                spoof_sel[0] = min(max(0, len(results) - 1), spoof_sel[0] + 1)
            elif key.code == term.KEY_ENTER or str(key) in ("\n", "\r"):
                if results:
                    threading.Thread(target=_do_spoof,
                                     args=(results[spoof_sel[0]],), daemon=True).start()
                view[0] = "menu"
            elif ks in ("Q", "\x1b") or key.code == term.KEY_ESCAPE:
                view[0] = "menu"
            elif is_mouse_click(key):
                view[0] = "menu"
            continue

        # ── menu view ─────────────────────────────────────────────────────────
        if key.code == term.KEY_UP or mouse_scroll_up(key):
            sel[0] = (sel[0] - 1) % n
            msg[0] = ""
        elif key.code == term.KEY_DOWN or mouse_scroll_down(key):
            sel[0] = (sel[0] + 1) % n
            msg[0] = ""
        elif key.code in (term.KEY_ENTER, term.KEY_LEFT, term.KEY_RIGHT) or str(key) in ("\n", "\r", " "):
            _, _, fkey = ITEMS[sel[0]]
            _toggle(fkey)
            msg[0] = "\u2713 Saved"
        elif ks == "S":
            # ARP scan
            if not _beta_on[0]:
                msg[0] = "\u26a0 Enable Beta Features first"
            else:
                view[0] = "scan"
                scan_state[0] = "scanning"
                scan_result[0] = None
                t = threading.Thread(target=_do_scan, daemon=True)
                t.start()
        elif ks == "R":
            # Restore original MAC
            if _spoofed[0]:
                if IS_WIN:
                    adapter = _get_wifi_adapter_win()
                    ok = restore_mac(adapter) if adapter else False
                else:
                    ok = restore_mac("wlan0")
                msg[0] = "\u2713 MAC restored" if ok else "\u26a0 Restore failed"
            else:
                msg[0] = "\u26a0 No active spoof to restore"
        elif ks in ("Q", "\x1b") or key.code == term.KEY_ESCAPE:
            break
        elif is_mouse_click(key):
            break

    return settings
