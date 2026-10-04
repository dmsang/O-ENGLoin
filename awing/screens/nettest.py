"""awing/screens/nettest.py — Network speed test & diagnostics screen."""
import threading, time
from awing import (term, bold, C_TITLE, C_BORDER, C_SEL, C_OK, C_ERR, C_WARN,
                   C_DIM, C_KEY, C_VAL, RST, render, center_in, box_top,
                   box_mid, box_bot, box_row, is_mouse_click, SPIN,
                   get_local_ip, ping_host, run_speedtest_threaded)

def network_test_screen(settings):
    initial_local = get_local_ip()
    result   = [{"local_ip": initial_local}]
    phase    = ["idle"]   # idle | running | done | error
    ping_r   = [None]     # (avg_ms, loss_pct)
    stop_ev  = threading.Event()

    def do_test():
        phase[0] = "running"
        result[0]["local_ip"] = get_local_ip()
        result[0]["phase"] = "Pinging 8.8.8.8..."
        avg_ms, loss = ping_host("8.8.8.8", count=3)
        ping_r[0] = (avg_ms, loss)
        if stop_ev.is_set():
            phase[0] = "idle"
            return

        run_speedtest_threaded(result[0], stop_ev)
        if stop_ev.is_set():
            phase[0] = "idle"
        elif result[0].get("phase") == "error":
            phase[0] = "error"
        else:
            phase[0] = "done"

    spin_i = [0]

    def build():
        W = term.width or 80; H = term.height or 24
        bw = min(72, W - 4); bh = 15; bx = max(0, (W - bw) // 2); by = max(0, (H - bh) // 2)
        rows = [""] * H

        rows[by]   = " " * bx + box_top(bw, " NETWORK TEST ")
        rows[by+1] = " " * bx + box_row(bw, center_in(C_TITLE + bold(" Network Diagnostics & Speed Test "), bw - 2))
        rows[by+2] = " " * bx + box_mid(bw)

        ph = result[0].get("phase", "") if result[0] else ""
        r  = by + 3

        if phase[0] == "idle":
            rows[r] = " " * bx + box_row(bw, center_in(C_KEY + "Enter" + RST + " start test   " + C_KEY + "Q / Esc" + RST + " back", bw - 2)); r += 1
        elif phase[0] == "running":
            spin = SPIN[spin_i[0] % len(SPIN)]; spin_i[0] += 1
            rows[r] = " " * bx + box_row(bw, "  " + C_WARN + spin + " " + ph + RST); r += 1
        elif phase[0] == "done":
            rows[r] = " " * bx + box_row(bw, center_in(C_OK + bold("✓ Network Test Completed Successfully") + RST, bw - 2)); r += 1
        elif phase[0] == "error":
            err = result[0].get("error") or "Unknown error"
            rows[r] = " " * bx + box_row(bw, "  " + C_ERR + "✗ Error: " + err + RST); r += 1
        else:
            rows[r] = " " * bx + box_mid(bw); r += 1

        rows[r] = " " * bx + box_mid(bw); r += 1

        # Local IP (Machine IP)
        lip = result[0].get("local_ip") or initial_local
        rows[r] = " " * bx + box_row(bw, "  Local IP (LAN) : " + (C_VAL + lip + RST if lip else C_DIM + "--" + RST)); r += 1

        # Public IP
        pip = result[0].get("public_ip")
        if pip:
            pip_disp = C_VAL + pip + RST
        elif phase[0] == "running" and not result[0].get("server"):
            pip_disp = C_DIM + "Detecting..." + RST
        else:
            pip_disp = C_DIM + "--" + RST
        rows[r] = " " * bx + box_row(bw, "  Public IP (WAN): " + pip_disp); r += 1

        # Target Server
        srv = result[0].get("server")
        if srv:
            srv_disp = C_VAL + srv + RST
        elif phase[0] == "running" and ph in ("Finding best server...", "Pinging 8.8.8.8..."):
            srv_disp = C_DIM + "Finding best server..." + RST
        else:
            srv_disp = C_DIM + "--" + RST
        rows[r] = " " * bx + box_row(bw, "  Target Server  : " + srv_disp); r += 1

        # Ping
        if ping_r[0] is not None:
            avg_ms, loss = ping_r[0]
            if avg_ms is not None:
                if avg_ms < 40:    pc = C_OK
                elif avg_ms < 100: pc = C_WARN
                else:              pc = C_ERR
                p_str = pc + str(avg_ms) + " ms" + RST
                l_str = (C_ERR if (loss or 0) > 0 else C_OK) + str(loss or 0) + "%" + RST
            else:
                p_str = C_ERR + "Timeout" + RST
                l_str = C_ERR + "100%" + RST
            rows[r] = " " * bx + box_row(bw, "  Ping (8.8.8.8) : " + p_str + "   Loss: " + l_str); r += 1
        elif phase[0] == "running" and ph == "Pinging 8.8.8.8...":
            rows[r] = " " * bx + box_row(bw, "  Ping (8.8.8.8) : " + C_DIM + "Pinging..." + RST); r += 1
        else:
            rows[r] = " " * bx + box_row(bw, "  Ping (8.8.8.8) : " + C_DIM + "--" + RST); r += 1

        # Download
        dl = result[0].get("download")
        dl_pct = result[0].get("dl_pct", 0)
        bar_w = 20
        if dl is not None:
            if dl >= 50:   dc = C_OK
            elif dl >= 15: dc = C_WARN
            else:          dc = C_ERR
            filled = int(min(dl / 100 * bar_w, bar_w))
            bar = dc + "█" * filled + C_DIM + "░" * (bar_w - filled) + RST
            rows[r] = " " * bx + box_row(bw, "  Download       : " + dc + ("%.1f" % dl) + " Mbps" + RST + "  " + bar); r += 1
        elif phase[0] == "running" and ph == "Testing download...":
            filled = int(dl_pct / 100 * bar_w)
            bar = C_WARN + "█" * filled + C_DIM + "░" * (bar_w - filled) + RST
            rows[r] = " " * bx + box_row(bw, "  Download       : " + C_WARN + "Testing... " + RST + bar + " " + str(dl_pct) + "%"); r += 1
        else:
            rows[r] = " " * bx + box_row(bw, "  Download       : " + C_DIM + "--" + RST); r += 1

        # Upload
        ul = result[0].get("upload")
        ul_pct = result[0].get("ul_pct", 0)
        if ul is not None:
            if ul >= 25:   uc = C_OK
            elif ul >= 10: uc = C_WARN
            else:          uc = C_ERR
            filled = int(min(ul / 100 * bar_w, bar_w))
            bar = uc + "█" * filled + C_DIM + "░" * (bar_w - filled) + RST
            rows[r] = " " * bx + box_row(bw, "  Upload         : " + uc + ("%.1f" % ul) + " Mbps" + RST + "  " + bar); r += 1
        elif phase[0] == "running" and ph == "Testing upload...":
            filled = int(ul_pct / 100 * bar_w)
            bar = C_WARN + "█" * filled + C_DIM + "░" * (bar_w - filled) + RST
            rows[r] = " " * bx + box_row(bw, "  Upload         : " + C_WARN + "Testing... " + RST + bar + " " + str(ul_pct) + "%"); r += 1
        else:
            rows[r] = " " * bx + box_row(bw, "  Upload         : " + C_DIM + "--" + RST); r += 1

        # Fill remaining rows
        bot = by + bh - 1
        for rr in range(r, bot - 1):
            if rows[rr] == "":
                rows[rr] = " " * bx + box_mid(bw)

        # Hint
        if phase[0] == "idle":
            hint = C_KEY + "Enter" + RST + " start   " + C_KEY + "Q / Esc" + RST + " back"
        elif phase[0] == "running":
            hint = C_WARN + "Testing in progress..." + RST + "   " + C_KEY + "Q / Esc" + RST + " cancel"
        else:
            hint = C_KEY + "Enter" + RST + " retest   " + C_KEY + "Q / Esc" + RST + " back"
        rows[bot-1] = " " * bx + box_row(bw, " " + hint)
        rows[bot]   = " " * bx + box_bot(bw)
        return rows

    test_thread = [None]

    try:
        while True:
            render(build())
            with term.cbreak(): key = term.inkey(timeout=0.3)
            if key:
                ks = str(key).upper()
                if ks == "Q" or key.code == term.KEY_ESCAPE:
                    stop_ev.set()
                    break
                start_test = (key.code == term.KEY_ENTER or ks in ("\n", "\r"))
                # Mouse click anywhere inside the box starts/cancels
                if is_mouse_click(key) and not start_test:
                    start_test = True
                if start_test:
                    if phase[0] in ("idle", "done", "error"):
                        stop_ev.clear()
                        result[0] = {"local_ip": get_local_ip()}
                        ping_r[0] = None
                        phase[0] = "running"
                        test_thread[0] = threading.Thread(target=do_test, daemon=True)
                        test_thread[0].start()
                    elif phase[0] == "running" and is_mouse_click(key):
                        # Right/middle-click or second click cancels
                        stop_ev.set()
    finally:
        stop_ev.set()
