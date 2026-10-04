"""awing/screens/beta_screen.py — Beta Features management screen."""
import threading
import time

from awing import (IS_WIN, term, bold, C_TITLE, C_BORDER, C_SEL, C_OK, C_WARN,
                   C_ERR, C_DIM, C_KEY, C_VAL, C_DBG, RST, render, center_in,
                   box_top, box_mid, box_bot, box_row, sep_row, str_width,
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
        ("beta_arp",       "\u25ce  ARP MAC Bypass",  "arp"),
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
        bw = max(30, min(72, W - 4)); bx = max(0, (W - bw) // 2)

        rows[1] = " " * bx + box_top(bw, " \u26a1 BETA FEATURES ")
        rows[2] = " " * bx + box_row(bw, center_in(
            C_WARN + bold(" Experimental — may not work on all networks ") + RST, bw - 2))
        rows[3] = " " * bx + sep_row(bw)

        # Feature toggles
        for idx, (skey, label, fkey) in enumerate(ITEMS):
            val = _val(fkey)
            tog = (C_OK + bold("[ ON  ]") + RST) if val else (C_DIM + "[ OFF ]" + RST)
            dim = "" if (fkey == "master" or _beta_on[0]) else C_DIM
            pad_lbl = label + " " * max(0, 30 - str_width(label))
            if idx == sel[0]:
                content = C_SEL + "  " + pad_lbl + RST + " " + tog
            else:
                content = "  " + dim + pad_lbl + RST + " " + tog
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
                C_OK + "\u25ce ARP MAC Bypass" + RST + C_DIM + " — spoof MAC of a bypass device." + RST,
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
        bw = max(30, min(72, W - 4)); bx = max(0, (W - bw) // 2)

        if scan_state[0] == "scanning":
            bh = 8; by = max(1, (H - bh) // 2)
            rows = [""] * H
            rows[by]   = " " * bx + box_top(bw, " \u25ce ARP SCANNING ")
            rows[by+1] = " " * bx + box_row(bw, center_in(C_WARN + bold("\u29d7 Scanning Local Subnet...") + RST, bw - 2))
            prog_txt = scan_prog[0] or "Initialising scan..."
            rows[by+2] = " " * bx + box_row(bw, center_in(C_KEY + prog_txt[:bw-6] + RST, bw - 2))
            rows[by+3] = " " * bx + sep_row(bw)
            rows[by+4] = " " * bx + box_row(bw, C_DIM + "  Pinging subnet, reading ARP, measuring stability..." + RST)
            rows[by+5] = " " * bx + sep_row(bw)
            hint_txt = C_KEY + "Q / Esc" + RST + " cancel scan"
            rows[by+6] = " " * bx + box_row(bw, center_in(hint_txt, bw - 2))
            rows[by+7] = " " * bx + box_bot(bw)
            return rows

        if scan_state[0] == "error":
            bh = 6; by = max(1, (H - bh) // 2)
            rows = [""] * H
            rows[by]   = " " * bx + box_top(bw, " \u25ce ARP SCAN RESULTS ")
            rows[by+1] = " " * bx + box_row(bw, center_in(C_ERR + bold("\u2717 Scan Failed") + RST, bw - 2))
            err_msg = _arp_status[0].replace("error:", "") if _arp_status[0].startswith("error:") else "Scan failed"
            rows[by+2] = " " * bx + box_row(bw, "  " + C_ERR + err_msg[:bw-6] + RST)
            rows[by+3] = " " * bx + sep_row(bw)
            rows[by+4] = " " * bx + box_row(bw, center_in(C_KEY + "Enter / Q / Esc" + RST + " back", bw - 2))
            rows[by+5] = " " * bx + box_bot(bw)
            return rows

        results = scan_result[0] or []
        if not results:
            bh = 6; by = max(1, (H - bh) // 2)
            rows = [""] * H
            rows[by]   = " " * bx + box_top(bw, " \u25ce ARP SCAN RESULTS ")
            rows[by+1] = " " * bx + box_row(bw, center_in(C_WARN + "No bypass candidates found on this subnet." + RST, bw - 2))
            rows[by+2] = " " * bx + box_row(bw, center_in(C_DIM + "All devices require captive portal or subnet is empty." + RST, bw - 2))
            rows[by+3] = " " * bx + sep_row(bw)
            rows[by+4] = " " * bx + box_row(bw, center_in(C_KEY + "Enter / Q / Esc" + RST + " back", bw - 2))
            rows[by+5] = " " * bx + box_bot(bw)
            return rows

        max_show = min(10, max(3, H - 10))
        shown = results[:max_show]
        bh = 8 + len(shown)
        by = max(1, (H - bh) // 2)
        rows = [""] * H
        rows[by] = " " * bx + box_top(bw, " \u25ce ARP SCAN RESULTS ")
        rows[by+1] = " " * bx + box_row(bw, center_in(
            C_OK + bold(f"  Found {len(results)} candidate(s)  ") + RST, bw - 2))
        rows[by+2] = " " * bx + sep_row(bw)

        col_h = " #  " + "IP".ljust(17) + "MAC".ljust(20) + "Score".ljust(8) + "Vendor"
        rows[by+3] = " " * bx + box_row(bw, C_KEY + col_h + RST)
        rows[by+4] = " " * bx + sep_row(bw)

        for i, c in enumerate(shown):
            score_bar = int(c["score"] * 5) * "\u2588" + (5 - int(c["score"] * 5)) * "\u2591"
            score_clr = C_OK if c["score"] > 0.8 else C_WARN
            v_cut = max(8, bw - 58)
            line = (f" {i+1:<3}" +
                    c["ip"].ljust(17) +
                    c["mac"].ljust(20) +
                    score_clr + score_bar + RST + "  " +
                    C_DIM + c["vendor"][:v_cut] + RST)
            if i == spoof_sel[0]:
                rows[by+5+i] = " " * bx + box_row(bw, C_SEL + "  " + line + RST)
            else:
                rows[by+5+i] = " " * bx + box_row(bw, "  " + line)

        sep_r = by + 5 + len(shown)
        rows[sep_r] = " " * bx + sep_row(bw)
        hint = (C_KEY + "\u2191\u2193" + RST + " select   " +
                C_KEY + "Enter" + RST + " spoof MAC   " +
                C_KEY + "Q/Esc" + RST + " back")
        rows[sep_r + 1] = " " * bx + box_row(bw, center_in(hint, bw - 2))
        rows[sep_r + 2] = " " * bx + box_bot(bw)
        return rows

    _scan_stop = threading.Event()

    def _do_scan():
        scan_state[0] = "scanning"
        _arp_status[0] = "scanning"

        def progress(txt):
            scan_prog[0] = txt

        try:
            results = scan_bypass_candidates(settings, progress_cb=progress, stop_event=_scan_stop)
            if _scan_stop.is_set():
                scan_state[0] = "idle"
                _arp_status[0] = "idle"
                return
            scan_result[0] = results
            scan_state[0] = "done"
            _arp_status[0] = "idle"
            spoof_sel[0] = 0
        except Exception as e:
            if _scan_stop.is_set():
                scan_state[0] = "idle"
                _arp_status[0] = "idle"
                return
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

        timeout = 0.25 if (view[0] == "scan" and scan_state[0] == "scanning") else None
        with term.cbreak():
            key = term.inkey(timeout=timeout)

        if not key:
            continue

        n = len(ITEMS)
        ks = str(key).upper()
        kc = getattr(key, "code", None)

        if view[0] == "scan":
            if scan_state[0] == "scanning":
                if ks in ("Q", "\x1b") or kc == term.KEY_ESCAPE:
                    _scan_stop.set()
                    scan_state[0] = "idle"
                    _arp_status[0] = "idle"
                    view[0] = "menu"
                    msg[0] = "Scan canceled"
                continue

            results = scan_result[0] or []
            if not results or scan_state[0] == "error":
                if kc in (term.KEY_ENTER, term.KEY_ESCAPE) or ks in ("Q", "\x1b", "\n", "\r") or is_mouse_click(key):
                    view[0] = "menu"
                continue

            if kc == term.KEY_UP or mouse_scroll_up(key):
                spoof_sel[0] = max(0, spoof_sel[0] - 1)
            elif kc == term.KEY_DOWN or mouse_scroll_down(key):
                spoof_sel[0] = min(max(0, len(results) - 1), spoof_sel[0] + 1)
            elif kc == term.KEY_ENTER or str(key) in ("\n", "\r"):
                if results:
                    threading.Thread(target=_do_spoof,
                                     args=(results[spoof_sel[0]],), daemon=True).start()
                view[0] = "menu"
            elif ks in ("Q", "\x1b") or kc == term.KEY_ESCAPE:
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
                _scan_stop.clear()
                scan_state[0] = "scanning"
                scan_prog[0] = "Starting ARP scan..."
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
